from __future__ import annotations

from flask import Flask, jsonify, redirect, render_template, request, url_for
from flask_login import LoginManager, UserMixin, current_user, login_required, login_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash

from .config import DEFAULT_CONFIG
from .crawler import CrawlManager
from .db import Database
from .storage import Storage


class LocalUser(UserMixin):
    def __init__(self, user_id: str):
        self.id = user_id


login_manager = LoginManager()
login_manager.login_view = 'login'


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.config.update(DEFAULT_CONFIG)
    if test_config:
        app.config.update(test_config)

    app.config['PASSWORD_HASH'] = generate_password_hash(app.config['APP_PASSWORD'])

    database = Database(app.config)
    storage = Storage(database)
    storage.initialize()
    manager = CrawlManager(storage, app.config)

    app.extensions['crawl_manager'] = manager
    app.extensions['storage'] = storage

    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id: str):
        if user_id == app.config['APP_USERNAME']:
            return LocalUser(user_id)
        return None

    @app.get('/login')
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('index_page'))
        return render_template('login.html')

    @app.post('/login')
    def login_submit():
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        if username != app.config['APP_USERNAME'] or not check_password_hash(app.config['PASSWORD_HASH'], password):
            return render_template('login.html', error='Invalid credentials'), 401
        login_user(LocalUser(username))
        return redirect(url_for('index_page'))

    @app.post('/logout')
    @login_required
    def logout():
        logout_user()
        return redirect(url_for('login'))

    @app.get('/')
    @login_required
    def index_page():
        return render_template('index.html', username=current_user.id)

    @app.post('/api/index')
    @login_required
    def start_index():
        payload = request.get_json(silent=True) or request.form
        origin = (payload.get('origin') or '').strip()
        depth = int(payload.get('depth', 1))
        try:
            job = manager.start_job(origin, depth)
        except ValueError as exc:
            return jsonify({'error': str(exc)}), 400
        return jsonify(job), 202

    @app.get('/api/search')
    @login_required
    def search():
        query = request.args.get('q', '')
        limit = int(request.args.get('limit', 50))
        return jsonify(manager.search(query, limit=limit))

    @app.get('/api/status')
    @login_required
    def status():
        return jsonify(manager.status())

    @app.post('/api/shutdown')
    @login_required
    def shutdown():
        manager.shutdown()
        return jsonify({'status': 'stopped'})

    return app