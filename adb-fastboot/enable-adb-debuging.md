# Revive Android Device Guide

**NOTE:** This process requires an unlocked bootloader.
Since Android 9 /data/property/persist.sys.usb.config no more exists. Now there's only one file: /data/property/persistent_properties. And that too isn't plain text but includes arbitrary characters. Even after editing that, adb authentication won't work without extra steps


1. Connect the device to your Mac or PC in recovery mode. If the screen is broken, you may need to map the process mentally.
2. Open a terminal or Command Prompt on your computer and navigate to the platform-tools directory. Type and enter `./adb devices` to check if the device is connected in recovery mode.
3. Mount the data and system directories using the following commands:
   ```
   ./adb shell mount data
   ./adb shell mount system
   ```
4. Get the persist.sys.usb.config file from your device using:
   ```
   ./adb pull /data/property/persist.sys.usb.config /YourDirectory
   ```
5. Open the persist.sys.usb.config file in a text editor, edit it to `mtp,adb`, and save the changes.
6. Push the modified file back to the device:
   ```
   ./adb push /YourDirectory/persist.sys.usb.config /data/property
   ```
7. Get the build.prop file from the device:
   ```
   ./adb pull /system/build.prop /YourDirectory
   ```
8. Add the following lines to the build.prop file:
   ```
   persist.service.adb.enable=1
   persist.service.debuggable=1
   persist.sys.usb.config=mtp,adb
   ```
9. Push the modified build.prop file back to the device:
   ```
   ./adb push /YourDirectory/build.prop /system/
   ```

By following these steps, you have enabled USB debugging on your device. However, you may still encounter issues with RSA verification. If you have any insights on bypassing this verification or other methods for reviving a dead phone, please share them. Your help is greatly appreciated!
