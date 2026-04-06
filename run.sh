pip install -U --prefix .local -r requirements.txt
pip install -U --prefix .local ytdlp-jsc --only-binary=:all: --target ~/.yt-dlp/plugins/
/usr/local/bin/python /home/container/main.py