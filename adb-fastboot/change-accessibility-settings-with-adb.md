# Fetched from
https://gist.github.com/mrk-han/67a98616e43f86f8482c5ee6dd3faabe

# Using ADB to control Accessbility settings for easier testing with Android Emulators + Real Devices

It's a lot easier to test accessibility on the fly using ADB. This gist attempts to make the days of navigating through the Android device settings UI to change Accessibility settings obsolete.

These ADB commands will hopefully encourage Android developers to test and use their apps with common Accessiblility settings enabled.

**Credit to James Nitsch** for inspiring this, and for figuring out the `put` commands to enable these settings.

## Font Scale (Font Size -- Testing Dynamic Text)

`adb shell settings put system font_scale 0.85` (small)

`adb shell settings put system font_scale 1.0` (default)

`adb shell settings put system font_scale 1.15` (large)

`adb shell settings put system font_scale 1.30` (largest)

`adb shell settings put system font_scale 2.0` (sizes like this can only be achieved with custom adb setting, not from ui)

## Talkback

**disable talkback**

```
adb shell settings put secure enabled_accessibility_services com.android.talkback/com.google.android.marvin.talkback.TalkBackService
```

**enable talkback**

```
adb shell settings put secure enabled_accessibility_services com.google.android.marvin.talkback/com.google.android.marvin.talkback.TalkBackService
```

## Color

**Properties:**
```
accessibility_display_daltonizer_enabled=1
accessibility_display_daltonizer=11
accessibility_display_daltonizer=12
accessibility_display_daltonizer=13
```

**Examples:**

`adb shell settings put secure accessibility_display_daltonizer_enabled 1`

`adb shell settings put secure accessibility_display_daltonizer 0`

`adb shell settings put secure accessibility_display_daltonizer 11`

`adb shell settings put secure accessibility_display_daltonizer 12`

`adb shell settings put secure accessibility_display_daltonizer 13`

```
0 == Monochromatic
11 is for Deuteranomaly (red-green)
12 is for Protanomaly (red-green)
13 is for Tritanomaly (blue-yellow)
```

## Color Inversion

**Property:** `accessibility_display_inversion_enabled=1`

**ADB Command:** `adb shell settings put secure accessibility_display_inversion_enabled 1`

## High Contrast Text

**Property:** `high_text_contrast_enabled=1`

**ADB Command:** `adb shell settings put secure high_text_contrast_enabled 1`

## Magnification

Set: `adb shell settings put secure accessibility_display_magnification_scale 5.0`

Enable: `adb shell settings put secure accessibility_display_magnification_enabled 1`

Disable: `adb shell settings put secure accessibility_display_magnification_enabled 0`

## List Existing Properties

```
adb shell settings list system
adb shell settings list global
adb shell settings list secure
```

Also, `adb shell getprop` is a great way to expose a lot of other properties you can change with the `adb shell setprop` functionality


## Show Touches

`adb shell settings put system show_touches 1`

## Pointer Location

`adb shell settings put system pointer_location 1`

https://developer.android.com/reference/android/provider/Settings
