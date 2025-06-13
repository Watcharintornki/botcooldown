from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "Server is running!"

if __name__ == "__main__":
    port = 8080  # กำหนดพอร์ตตรงนี้เลย เช่น 5000
    app.run(host='0.0.0.0', port=port)
