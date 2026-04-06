pip install -U --prefix .local -r requirements.txt
pip install -U --target ~/.yt-dlp/plugins/ ytdlp-jsc --only-binary=:all: 
/usr/local/bin/python /home/container/main.py