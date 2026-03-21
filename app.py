from crawler.app import create_app

app = create_app()


if __name__ == '__main__':
    host = app.config.get('APP_HOST', '127.0.0.1')
    port = int(app.config.get('APP_PORT', 5000))
    app.run(host=host, port=port, debug=app.config.get('DEBUG', False))