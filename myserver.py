from flask import Flask
from threading import Thread

app = Flask(__name__)

@app.route('/')
def home():
    return "Server is running!"

if __name__ == "__main__":
    app.run(host='0.0.0.0', port = 8080)

def __main__():
    thred = Thread(target = run)
    thred.start()
