# X11 fallback (older Raspberry Pi OS images / manually switched from Wayland)

If your Pi OS image still defaults to X11 instead of labwc, the systemd
`--user` service in `p1s-touchscreen.service` still works the same way
(swap `Environment=QT_QPA_PLATFORM=wayland` for `xcb`, or just delete that
line and let Qt auto-detect). For autostart + screen behavior:

1. **Autostart**: add to `~/.config/lxsession/LXDE-pi/autostart` (or your
   session's autostart file):
   ```
   @systemctl --user start p1s-touchscreen.service
   ```

2. **Disable screen blanking/DPMS**:
   ```
   @xset s off
   @xset s noblank
   @xset -dpms
   ```

3. **Hide the cursor** when idle (the app already blanks the cursor over
   its own window via `Qt.CursorShape.BlankCursor`, but `unclutter` covers
   any WM chrome around it):
   ```
   sudo apt install unclutter
   @unclutter -idle 0
   ```

Not designed in further depth here -- Bookworm's default is labwc/Wayland
(see `autostart-labwc.desktop`), so treat this as a fallback to adapt if
needed rather than a fully maintained second path.
