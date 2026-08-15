import os
from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from config import get_config

app = Flask(__name__)
app.config.from_object(get_config())
db = SQLAlchemy(app)


class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False, default='Action')
    download_link = db.Column(db.String(200), nullable=False)
    image_url = db.Column(db.String(200), nullable=True)


def login_required(view):
    def wrapped(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('login'))
        return view(*args, **kwargs)

    wrapped.__name__ = view.__name__
    return wrapped


def ensure_schema():
    inspector = db.inspect(db.engine)
    columns = [column['name'] for column in inspector.get_columns('game')]
    if 'category' not in columns:
        with db.engine.begin() as connection:
            connection.execute(text("ALTER TABLE game ADD COLUMN category VARCHAR(50) NOT NULL DEFAULT 'Action'"))


def seed_games():
    if Game.query.first() is not None:
        return

    games = [
        {
            'title': 'Neon Drift',
            'description': 'High-speed street racing through a glowing futuristic city.',
            'category': 'Racing',
            'download_link': 'https://example.com/neon-drift',
            'image_url': 'https://images.unsplash.com/photo-1542751371-adc38448a05e?auto=format&fit=crop&w=900&q=80'
        },
        {
            'title': 'Shadow Strike',
            'description': 'Covert missions, precision attacks, and silent tactical operations.',
            'category': 'Action',
            'download_link': 'https://example.com/shadow-strike',
            'image_url': 'https://images.unsplash.com/photo-1511512578047-dfb367046420?auto=format&fit=crop&w=900&q=80'
        },
        {
            'title': 'Skyline Quest',
            'description': 'Explore floating kingdoms and ancient ruins in this epic adventure.',
            'category': 'Adventure',
            'download_link': 'https://example.com/skyline-quest',
            'image_url': 'https://images.unsplash.com/photo-1511884642898-4c92249e20b6?auto=format&fit=crop&w=900&q=80'
        },
        {
            'title': 'Quantum Clash',
            'description': 'Compete in a cyber war with ultra-fast weapons and battle tactics.',
            'category': 'Shooter',
            'download_link': 'https://example.com/quantum-clash',
            'image_url': 'https://images.unsplash.com/photo-1528819622761-6bcf002c2d8d?auto=format&fit=crop&w=900&q=80'
        },
        {
            'title': 'Grid Empire',
            'description': 'Build, expand, and dominate a neon empire of strategic resources.',
            'category': 'Strategy',
            'download_link': 'https://example.com/grid-empire',
            'image_url': 'https://images.unsplash.com/photo-1550745165-9bc0b252726f?auto=format&fit=crop&w=900&q=80'
        },
        {
            'title': 'Turbo Arena',
            'description': 'A fast-paced sports battle with futuristic vehicles and skill boosts.',
            'category': 'Sports',
            'download_link': 'https://example.com/turbo-arena',
            'image_url': 'https://images.unsplash.com/photo-1517649763962-0c623066013b?auto=format&fit=crop&w=900&q=80'
        },
    ]

    for item in games:
        db.session.add(Game(**item))

    db.session.commit()


with app.app_context():
    db.create_all()
    ensure_schema()
    seed_games()


@app.route('/')
def home():
    search_query = request.args.get('q', '').strip()
    selected_category = request.args.get('category', 'All')
    games_query = Game.query

    if selected_category and selected_category.lower() != 'all':
        games_query = games_query.filter(Game.category.ilike(selected_category))

    if search_query:
        games_query = games_query.filter(
            (Game.title.ilike(f'%{search_query}%')) |
            (Game.description.ilike(f'%{search_query}%'))
        )

    games = games_query.order_by(Game.id.desc()).all()
    categories = ['All', 'Action', 'Racing', 'Adventure', 'Strategy', 'Shooter', 'Sports']
    return render_template('index.html', games=games, search_query=search_query, categories=categories, selected_category=selected_category)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form.get('password', '')
        if password == 'Nanayaw1@2008':
            session['admin_logged_in'] = True
            return redirect(url_for('admin'))
        return render_template('login.html', error='Incorrect password. Please try again.')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/admin', methods=['GET', 'POST'])
@login_required
def admin():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('desc', '').strip()
        link = request.form.get('link', '').strip()
        image = request.form.get('img', '').strip()
        category = request.form.get('category', 'Action').strip()

        if not title or not link:
            return redirect(url_for('admin'))

        new_game = Game(
            title=title,
            description=description or 'New cyber game added to the archive.',
            category=category,
            download_link=link,
            image_url=image or 'https://images.unsplash.com/photo-1511512578047-dfb367046420?auto=format&fit=crop&w=900&q=80'
        )
        db.session.add(new_game)
        db.session.commit()
        return redirect(url_for('admin'))

    games = Game.query.order_by(Game.id.desc()).all()
    return render_template('admin.html', games=games)


@app.route('/delete/<int:id>')
@login_required
def delete_game(id):
    game_to_delete = Game.query.get_or_404(id)
    db.session.delete(game_to_delete)
    db.session.commit()
    return redirect(url_for('admin'))


if __name__ == '__main__':
    # Development only - Production uses Gunicorn
    app.run(debug=os.getenv('FLASK_ENV') == 'development', host='0.0.0.0', port=int(os.getenv('PORT', 5000)))