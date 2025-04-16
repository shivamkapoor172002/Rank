from app import app
from init_app import init_app

if __name__ == '__main__':
    init_app(app)
    app.run(debug=True, port=5000)