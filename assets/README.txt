Window icon (VS Queue Monitor)
--------------------------------
app_icon.gif matches the bytes in monitor.py (_APP_ICON_GIF_B64).

To change the icon: edit or replace app_icon.gif, then re-embed in monitor.py, for example:

  python -c "import base64, pathlib; b=pathlib.Path('assets/app_icon.gif').read_bytes(); s=base64.b64encode(b).decode(); print(repr(s))"

Split the printed string into concatenated line chunks (~88 chars) for _APP_ICON_GIF_B64.

The app loads the icon only from the embedded constant so monitor.py stays a single-file drop-in.
