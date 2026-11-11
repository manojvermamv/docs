# ADB Commands Cheat Sheet
https://gist.github.com/mrk-han/4bb41702f317c2534055d30acaa4ff9b


## ADB Devices
```bash
adb usb
adb root                          # Restarts adbd with root permissions
adb devices                       # List of connected devices
adb devices -l                    # List of connected devices by product/model
adb connect <IP>:<PORT>           # Connect to an remote adb device via ipaddress (Note: By default port is 5555)
adb -s <deviceName> <command>     # Redirect command to specific device (Ex: adb -s 127.0.0.1:5555 shell)
adb –d <command>                  # Directs command to only attached USB device
adb wait-for-device
```

## ADB Server
```bash
adb tcpip 5555                    # Start adb server on port 5555
adb kill-server
adb start-server
```

## Port Tunneling
In case the adb port is only accessible from localhost in the android device but you have access via SSH, you can forward the port 5555 and connect via adb:
```bash
ssh -i ssh_key username@10.10.10.10 -L 5555:127.0.0.1:5555 -p 2222
adb connect 127.0.0.1:5555
```

## ADB Shell
```bash
adb shell    # Open or run commands in a terminal on the host Android device.
```

## ADB Reboot Device
```bash
adb reboot
adb reboot -p
adb shell reboot -p
adb reboot recovery
adb reboot bootloader
adb reboot-bootloader
```

## LogCat
```bash
adb logcat [options] [filter] [filter]     # View device log
adb logcat -c                     # clear The parameter -c will clear the current logs on the device.
adb logcat -d > [path_to_file]    # Save the logcat output to a file on the local system.
adb bugreport > [path_to_file]    # Will dump the whole device information like dumpstate, dumpsys, and logcat output.
```

## Background execution
nohup (no hangup) allows the command to run even after the terminal is closed
```bash
nohup some_command > /dev/null 2>&1&        # Run a command that survives the end of its terminal.
```


## Permissions
```bash
adb shell permissions groups                           # List permission groups definitions
adb shell list permissions -g -r                       # List permissions details
adb shell pm grant [package_name] [Permission]         # Grant a permission to an app. 
adb shell pm revoke [package_name] [Permission]        # Revoke a permission from an app.
adb shell pm reset-permissions -p [package_name]
Example:
adb shell pm grant com.android.package android.permission.READ_SMS
```

## Files
```bash
run-as <package> cat <file>        # Access the private package files
adb push [source] [destination]    # Copy files from your computer to your phone.
adb pull [device file location] [local file location]    # Copy files from your phone to your computer.
adb shell find /sdcard/ -iname "*file_name*" -type f     # Find files in android file system
```

## App Install
```bash
adb -e install path/to/app.apk
adb shell install <apk/path>
adb devices | tail -n +2 | cut -sf 1 | xargs -IX adb -s X install -r apk_file_path.apk  # Install the given app on all connected devices.
```

## Uninstalling App from Device
```bash
adb uninstall app.package.name              # Uninstall app
adb uninstall -k app.package.name           # Uninstall app without deleting data
adb shell pm clear app.package.name         # Deletes all data associated with a package.
adb shell pm uninstall app.package.name
```

## Update App
```bash
adb install -r apk_file_path.apk    # -r means re-install the app and keep its data on the device.
adb install –k apk_file_path_on_computer
```

## Device Backups 
```bash
adb backup -apk -all -f backup.ab                  # Backup settings and apps
adb backup -apk -shared -all -f backup.ab          # Backup settings, apps and shared storage
adb backup -apk -nosystem -all -f backup.ab        # Backup only non-system apps
adb backup -apk [package_name] -f backup_app.ab    # Backup single app data
adb restore backup.ab                              # Restore a previous backup
```

## Activity Manager
```bash
adb shell am start [<options>]          # Start an activity. Without options you can see the help menu
adb shell am startservice [<options>]   # Start a service. Without options you can see the help menu
adb shell am broadcast [<options>]      # Send a broadcast. Without options you can see the help menu

adb shell am start -a android.intent.action.VIEW -d URL       # Opens URL
adb shell am start -t image/* -a android.intent.action.VIEW   # Opens gallery
adb shell am start -W -c android.intent.category.HOME -a android.intent.action.MAIN   # Home Button

adb shell am start -a android.intent.action.SENDTO -d sms:+910123456789 --es sms_body "Test Message" --ez exit_on_sent true
adb shell input keyevent 22
adb shell input keyevent 66

adb shell am start -a android.intent.action.CALL -d tel:+972527300294    # Make a call
adb shell am start -a android.intent.action.VIEW
adb shell am broadcast -a 'my_action'
```

## Package Info
adb shell pm list packages [-f] [-d] [-e] [-s] [-3] [-i] [-l] [-u] [-U] [--uid UID] [--user USER_ID] [FILTER]
<br>Prints all packages; optionally only those whose name contains the text in FILTER.
    <br>Options:
    <br>-f: see their associated file
    <br>-d: filter to only show disabled packages
    <br>-e: filter to only show enabled packages
    <br>-s: filter to only show system packages
    <br>-3: filter to only show third party packages
    <br>-i: see the installer for the packages
    <br>-l: ignored (used for compatibility with older releases)
    <br>-U: also show the package UID
    <br>-u: also include uninstalled packages
    <br>--uid UID: filter to only show packages with the given UID
    <br>--user USER_ID: only list packages belonging to the given user
```bash
adb shell pm list packages                  # Lists package names
adb shell pm list packages -r               # Lists package name + path to apks
adb shell pm list packages -3               # Lists third party package names
adb shell pm list packages -s               # Lists only system packages
adb shell pm list packages -u               # Lists package names + uninstalled
adb shell pm list packages                  # Lists package names
adb shell pm dump <package_name>            # Lists info on one package
adb shell pm path <package_name>            # Path to the apk file
# Print all apks paths
adb shell pm list packages | sed -e "s/package://" | while read x; do cmd package resolve-activity $x | grep -w "sourceDir=" | grep -v "Apks not found"; done
# Print all applications with its launcher activity
adb shell pm list packages | sed -e "s/package://" | while read x; do cmd package resolve-activity --brief $x | tail -n 1 | grep -v "No activity found"; done
```

## Print Text
```bash
adb shell input text 'Wow, it's so cool feature'
```

## Screenshot/Screenrecord
```bash
adb shell screencap -p /sdcard/screenshot.png     # Taking a screenshot of a device display.

adb shell screenrecord /sdcard/demo.mp4           # Taking a screenrecord of a device display. Optional args as below
adb shell screenrecord --size <WIDTHxHEIGHT>
adb shell screenrecord --bit-rate <RATE>
adb shell screenrecord --time-limit <TIME>        # Sets the maximum recording time, in seconds. The default and maximum value is 180 (3 minutes).
adb shell screenrecord --rotate                   # Rotates 90 degrees
adb shell screenrecord --verbose
```

## Key Event
```bash
adb shell input keyevent 3    # Home btn
adb shell input keyevent 4    # Back btn
adb shell input keyevent 5    # Call
adb shell input keyevent 6    # End call
adb shell input keyevent 26    # Turn Android device ON and OFF. It will toggle the device to on/off status.
adb shell input keyevent 27    # Camera
adb shell input keyevent 64    # Open browser
adb shell input keyevent 66    # Enter
adb shell input keyevent 67    # Delete (backspace)
adb shell input keyevent 207    # Contacts
adb shell input keyevent 220 / 221    # Brightness down/up
adb shell input keyevent 277 / 278 /279    # Cut/Copy/Paste
```

## Shared Preferences
Usage and explanations, please refer to the [PreferencesEditor](https://github.com/jfsso/PreferencesEditor/tree/master).
```bash
# replace org.example.app with your application id

# Add a value to default shared preferences.
adb shell 'am broadcast -a org.example.app.sp.PUT --es key key_name --es value "hello world!"'

# Remove a value to default shared preferences.
adb shell 'am broadcast -a org.example.app.sp.REMOVE --es key key_name'

# Clear all default shared preferences.
adb shell 'am broadcast -a org.example.app.sp.CLEAR --es key key_name'

# It's also possible to specify shared preferences file.
adb shell 'am broadcast -a org.example.app.sp.PUT --es name Game --es key level --ei value 10'

# Data types
adb shell 'am broadcast -a org.example.app.sp.PUT --es key string --es value "hello world!"'
adb shell 'am broadcast -a org.example.app.sp.PUT --es key boolean --ez value true'
adb shell 'am broadcast -a org.example.app.sp.PUT --es key float --ef value 3.14159'
adb shell 'am broadcast -a org.example.app.sp.PUT --es key int --ei value 2015'
adb shell 'am broadcast -a org.example.app.sp.PUT --es key long --el value 9223372036854775807'

# Restart application process after making changes
adb shell 'am broadcast -a org.example.app.sp.CLEAR --ez restart true'
```

## Monkey
```bash
adb shell monkey -p app.package.name                   # Starts the specified package
adb shell monkey -p app.package.name -v 10000 -s 100   # Monkey tool generates 10,000 random events on the real device
```

## Other
```bash
adb backup    # Create a full backup of your phone and save it to the computer.
adb restore    # Restore a backup to your phone.
adb sideload    # Push and flash custom ROMs and zips from your computer.
```

## Wifi
```bash
adb shell svc wifi enable                  # Enable mobile wifi.
adb shell svc wifi disable                 # Disable mobile wifi.
adb shell cmd -w wifi connect-network Public open                  # Connect to an open wifi network.
adb shell cmd -w wifi connect-network Redmi9Prime wpa2 password    # Connect to an secured wifi network.
```

## Enable hotspot tethering
The first command opens the Settings page for Tethering and Hotspot, while the latter simulate key presses: Down and Enter, respectively.
```bash
adb shell am start -n com.android.settings/.TetherSettings
adb shell input keyevent 20     # Press Down
adb shell input keyevent 66     # Press Enter 
```

## Unlock pin screen lock
```bash
adb shell input keyevent 82     # 1. Pressing the lock button
adb shell input keyevent 66     # 2. Pressing the lock button
adb shell input keyevent 26     # 3. Pressing the lock button
adb shell input touchscreen swipe 930 880 930 380      # Swipe UP
adb shell input text XXXX       # Entering your passcode
adb shell input keyevent 66     # Pressing Enter
```

## Root Commands
```bash
adb shell "su -c ls"   # list working directory with su rights.
adb shell "su -c echo anytext > /data/test.file"
```

## Set system-level preferences
```bash
adb shell settings put secure location_mode 0                   # Enable (Value: 3) / Disable (Value: 0) location.
adb shell settings put global heads_up_notifications_enabled 0  # Enable (Value: 1) / Disable (Value: 0) pop-up notifications.
adb shell settings put global always_finish_activities 0        # Enable (Value: 1) / Disable (Value: 0) aggressive finishing of activities and processes.
adb shell settings put system accelerometer_rotation 0          # Enable (Value: 1) / Disable (Value: 0) auto-rotation of the device.
adb shell settings put system user_rotation 3                   # (0° rotation: 0 / 90° rotation: 1 / 180° rotation: 2 / 270°  rotation: 3) clockwise rotate the device.
```

## Get system and device properties using getprop
```bash
adb shell getprop -T        # Provides a list of system property types. (Important: this command can only be used on Android version 8.1 and above.)
adb shell getprop gsm.sim.operator.alpha         # Provides SIM Operator
adb shell getprop ro.build.version.release       # Provides device android version
adb shell getprop ro.boot.wifimacaddr            # Provides the WiFi Mac Address
adb shell getprop ro.product.manufacturer        # Provides Android device manufacturer details
adb shell getprop ro.vendor.product.model        # Provides Android device product number
adb shell getprop ro.board.platform              # Provides Soc info
adb shell getprop ro.oem_unlock_supported        # Provides OEM unlock status
adb shell getprop ro.crypto.state                # Provides device encryption status
adb shell getprop ro.vendor.product.model        # Provides device model
adb shell getprop ro.bootimage.build.fingerprint # Provides Android device build fingerprint
adb shell getprop ro.cdma.home.operator.alpha    # Provides SIM operator name
adb shell getprop ro.system.build.version.sdk    # Provides API level
```

## Get diagnostic output for system services using dumpsys
[dumpsys](https://developer.android.com/studio/command-line/dumpsys) is a tool that runs on Android devices and offers information on system services. adb shell dumpsys commands provide vital diagnostic output for system services operating on a connected device

** Activities
```bash
adb shell dumpsys activity <package_name>/<activity_name>  # Provides complete activity info
adb shell dumpsys activity -p <package_name>   # Provides complete activity history for the given package
adb shell dumpsys window windows | grep -E 'mCurrentFocus|mFocusedApp'  # Prints current app’s opened activity
adb shell dumpsys activity -p <package_name> activities  # Provides activity manager activities that contain main stack, running activities, and recent tasks
adb shell dumpsys activity -p <package_name> activities | grep -E 'mResumedActivity'  # Prints current app’s resumed activity
adb shell dumpsys activity -p <package_name> services  # Provides list of services running for the given package
adb shell dumpsys activity -p <package_name> providers  # Provides list of current content providers for the given package
adb shell dumpsys activity -p <package_name> recents  # Provides list of recent tasks for the given package
adb shell dumpsys activity -p <package_name> broadcasts  # Provides list of broadcast states for the given package
adb shell dumpsys activity -p <package_name> intents  # Provides list of pending intents for the given package
adb shell dumpsys activity -p <package_name> permissions  # Provides list of permissions for the given package
adb shell dumpsys activity -p <package_name> processes  # Provides list of running processes for the given package
```

** Device Info
```bash
adb get-statе                     # Print device state
adb get-serialno                  # Get the serial number
adb shell netstat                 # List TCP connectivity
adb shell pwd                     # Print current working directory
adb shell pm list features        # List phone features
adb shell service list            # List all services
adb shell ps                      # Print process status
adb shell wm size                 # Displays the current screen resolution

adb shell wm size WidthxHeight    # Set the screen resolution to WxH
adb shell wm density 288          # Set the screen dessity (dpi)
adb shell wm size reset           # Reset to default
adb shell wm density reset        # Reset to default

adb shell dumpsys batterystats    # Collects battery data from your device
adb shell dumpsys battery         # Provides info on battery usage
adb shell dumpsys meminfo         # Provides info on memory usage
adb shell dumpsys cpuinfo         # Provides info on CPU usage
adb shell dumpsys display         # Provides info on display
adb shell dumpsys power           # Provides info on power statistics
adb shell dumpsys alarm           # Provides info on alarm
adb shell dumpsys location        # Provides info on location
adb shell dumpsys window displays                                                 # Provides info like pixel resolution, FPS, and DPI of the device’s display
adb shell dumpsys telephony.registry                                              # Gives information about wireless communication related parameters
adb shell "dumpsys bluetooth_manager | sed -n '/Bonded devices:/,/^$/p'"          # Gives information about connected bluetooth devices, mac addresses etc.

adb shell settings get secure android_id                                          # Get the Android ID
adb shell "service call iphonesubinfo 1 | cut -c 52-66 | tr -d '.[:space:]'"      # Get the IMEI
adb shell "service call iphonesubinfo 15 | cut -c 52-66 | tr -d '.[:space:]'"     # Get the Mobile Number
```

** Networks
```bash
adb shell dumpsys connectivity         # Provides the internet status and connectivity mode(cellular or Wi-Fi)
adb shell dumpsys network_management   # Provides all information about device network management
```

** Package
```bash
adb shell dumpsys package <package_name>   # Provides all the info about your app, ex: Version name/code, first install time, requested permissions, etc
```

** Input
```bash
adb shell dumpsys input      # Dumps the state of the system’s input devices, such as keyboards and touchscreens, and the processing of input events
```

## For more advanced

 Usage and explanations, please refer to the [ADB documentation](https://developer.android.com/studio/command-line/adb).
 <br> Addintional resources.
 <br> [1] <https://newandroidbook.com/ddb/S23/>
 
