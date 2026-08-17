import os
import re
from datetime import datetime
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from flask import Flask, render_template, request, redirect, url_for, session, send_file
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from werkzeug.security import generate_password_hash, check_password_hash
from config import get_config

app = Flask(__name__)
app.config.from_object(get_config())
db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    bio = db.Column(db.Text, nullable=True)
    profile_image = db.Column(db.String(200), nullable=True)
    favorite_games = db.Column(db.Text, nullable=True)  # Comma-separated game IDs
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False, default='Action')
    download_link = db.Column(db.String(200), nullable=False)
    affiliate_link = db.Column(db.String(300), nullable=True)
    store_name = db.Column(db.String(80), nullable=True, default='Store')
    store_type = db.Column(db.String(40), nullable=True, default='store')
    image_url = db.Column(db.String(200), nullable=True)
    video_url = db.Column(db.String(300), nullable=True)
    rating = db.Column(db.Float, nullable=False, default=4.5)
    reviews_count = db.Column(db.Integer, nullable=False, default=0)
    release_year = db.Column(db.Integer, nullable=False, default=2025)
    reviews = db.relationship('Review', backref='game', lazy=True)


class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey('game.id'), nullable=False)
    title = db.Column(db.String(120), nullable=False)
    author = db.Column(db.String(80), nullable=False, default='GamePulse')
    rating = db.Column(db.Float, nullable=False, default=4.5)
    excerpt = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class NewsPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(140), nullable=False)
    slug = db.Column(db.String(140), nullable=False, unique=True)
    category = db.Column(db.String(60), nullable=False, default='News')
    excerpt = db.Column(db.Text, nullable=False)
    body = db.Column(db.Text, nullable=False)
    published_at = db.Column(db.DateTime, default=datetime.utcnow)


class NewsletterSubscriber(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(180), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


def admin_login_required(view):
    def wrapped(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return view(*args, **kwargs)

    wrapped.__name__ = view.__name__
    return wrapped


def user_login_required(view):
    def wrapped(*args, **kwargs):
        if not session.get('user_logged_in'):
            return redirect(url_for('user_login'))
        return view(*args, **kwargs)

    wrapped.__name__ = view.__name__
    return wrapped


def ensure_schema():
    inspector = db.inspect(db.engine)
    if inspector.has_table('game'):
        columns = [column['name'] for column in inspector.get_columns('game')]
        if 'category' not in columns:
            with db.engine.begin() as connection:
                connection.execute(text("ALTER TABLE game ADD COLUMN category VARCHAR(50) NOT NULL DEFAULT 'Action'"))
        if 'rating' not in columns:
            with db.engine.begin() as connection:
                connection.execute(text("ALTER TABLE game ADD COLUMN rating FLOAT NOT NULL DEFAULT 4.5"))
        if 'reviews_count' not in columns:
            with db.engine.begin() as connection:
                connection.execute(text("ALTER TABLE game ADD COLUMN reviews_count INTEGER NOT NULL DEFAULT 0"))
        if 'release_year' not in columns:
            with db.engine.begin() as connection:
                connection.execute(text("ALTER TABLE game ADD COLUMN release_year INTEGER NOT NULL DEFAULT 2025"))
        if 'affiliate_link' not in columns:
            with db.engine.begin() as connection:
                connection.execute(text("ALTER TABLE game ADD COLUMN affiliate_link VARCHAR(300)"))
        if 'store_name' not in columns:
            with db.engine.begin() as connection:
                connection.execute(text("ALTER TABLE game ADD COLUMN store_name VARCHAR(80) DEFAULT 'Store'"))
        if 'store_type' not in columns:
            with db.engine.begin() as connection:
                connection.execute(text("ALTER TABLE game ADD COLUMN store_type VARCHAR(40) DEFAULT 'store'"))
        if 'video_url' not in columns:
            with db.engine.begin() as connection:
                connection.execute(text("ALTER TABLE game ADD COLUMN video_url VARCHAR(300)"))


def get_revenue_streams():
    return [
        {
            'title': '1. Affiliate game deals',
            'description': 'Earn commission when visitors buy games, bundles, and accessories through your curated recommendations.',
            'metric': '8-15% per sale',
            'highlight': 'Best for: Steam, Epic, Amazon, retailer links',
        },
        {
            'title': '2. Sponsored placements',
            'description': 'Sell homepage, review, or newsletter slots to gaming brands, studios, and launch campaigns.',
            'metric': '$150-$1,500/month',
            'highlight': 'Best for: game launches, hardware, teams, tournaments',
        },
        {
            'title': '3. Premium membership',
            'description': 'Offer early access to rankings, exclusive reviews, market insights, and member-only game lists.',
            'metric': '$9-$29/month',
            'highlight': 'Best for: loyal readers and competitive gamers',
        },
        {
            'title': '4. Email + lead capture',
            'description': 'Collect newsletter signups, promote deals, and monetize traffic with partner offers and paid promotions.',
            'metric': 'Lead gen + sponsorships',
            'highlight': 'Best for: daily gaming news and release alerts',
        },
        {
            'title': '5. Digital downloads + guides',
            'description': 'Sell game lists, cheat sheets, strategy guides, eBooks, and seasonal ranking packs as instant digital products.',
            'metric': '$5-$49 per product',
            'highlight': 'Best for: tactics guides, best-of lists, ownership packs',
        },
    ]


def build_affiliate_url(target_url, title, store_name='GamePulse'):
    if not target_url:
        return '#'

    parsed = urlparse(target_url)
    params = dict(parse_qsl(parsed.query, keep_blank_values=True))
    slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-') or 'game'
    params.update({
        'utm_source': 'gamepulse',
        'utm_medium': 'affiliate',
        'utm_campaign': slug,
        'utm_content': store_name.lower().replace(' ', '-')
    })
    return urlunparse(parsed._replace(query=urlencode(params)))


@app.context_processor
def inject_helpers():
    return {'affiliate_url_for': build_affiliate_url}


def update_game_store_links():
    affiliate_map = {
        'Neon Drift': ('https://store.steampowered.com/search/?term=Neon+Drift', 'Steam', 'steam'),
        'Shadow Strike': ('https://store.steampowered.com/search/?term=Shadow+Strike', 'Steam', 'steam'),
        'Skyline Quest': ('https://store.steampowered.com/search/?term=Skyline+Quest', 'Steam', 'steam'),
        'Quantum Clash': ('https://store.steampowered.com/search/?term=Quantum+Clash', 'Steam', 'steam'),
        'Grid Empire': ('https://store.steampowered.com/search/?term=Grid+Empire', 'Steam', 'steam'),
        'Turbo Arena': ('https://store.epicgames.com/en-US/browse?sortBy=relevancy&sortDir=DESC&keywords=Turbo%20Arena', 'Epic', 'epic'),
        'FIFA 27': ('https://store.epicgames.com/en-US/browse?sortBy=relevancy&sortDir=DESC&keywords=FIFA%2027', 'Epic', 'epic'),
    }

    for game in Game.query.all():
        target = affiliate_map.get(game.title)
        if target:
            game.affiliate_link = target[0]
            game.store_name = target[1]
            game.store_type = target[2]
            game.download_link = target[0]
        elif not game.affiliate_link:
            game.affiliate_link = game.download_link
            game.store_name = game.store_name or 'Store'
            game.store_type = game.store_type or 'store'

    db.session.commit()


def seed_games():
    games = [
        {
            'title': 'Neon Drift',
            'description': 'High-speed street racing through a glowing futuristic city.',
            'category': 'Racing',
            'download_link': 'https://store.steampowered.com/search/?term=Neon+Drift',
            'affiliate_link': 'https://store.steampowered.com/search/?term=Neon+Drift',
            'store_name': 'Steam',
            'image_url': 'https://images.unsplash.com/photo-1542751371-adc38448a05e?auto=format&fit=crop&w=900&q=80',
            'video_url': 'https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4',
            'rating': 4.8,
            'reviews_count': 128,
            'release_year': 2025,
        },
        {
            'title': 'Shadow Strike',
            'description': 'Covert missions, precision attacks, and silent tactical operations.',
            'category': 'Action',
            'download_link': 'https://store.steampowered.com/search/?term=Shadow+Strike',
            'affiliate_link': 'https://store.steampowered.com/search/?term=Shadow+Strike',
            'store_name': 'Steam',
            'image_url': 'https://images.unsplash.com/photo-1511512578047-dfb367046420?auto=format&fit=crop&w=900&q=80',
            'video_url': 'https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.webm',
            'rating': 4.7,
            'reviews_count': 96,
            'release_year': 2024,
        },
        {
            'title': 'Skyline Quest',
            'description': 'Explore floating kingdoms and ancient ruins in this epic adventure.',
            'category': 'Adventure',
            'download_link': 'https://store.steampowered.com/search/?term=Skyline+Quest',
            'affiliate_link': 'https://store.steampowered.com/search/?term=Skyline+Quest',
            'store_name': 'Steam',
            'image_url': 'https://images.unsplash.com/photo-1511884642898-4c92249e20b6?auto=format&fit=crop&w=900&q=80',
            'video_url': 'https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4',
            'rating': 4.9,
            'reviews_count': 210,
            'release_year': 2025,
        },
        {
            'title': 'Quantum Clash',
            'description': 'Compete in a cyber war with ultra-fast weapons and battle tactics.',
            'category': 'Shooter',
            'download_link': 'https://store.steampowered.com/search/?term=Quantum+Clash',
            'affiliate_link': 'https://store.steampowered.com/search/?term=Quantum+Clash',
            'store_name': 'Steam',
            'image_url': 'https://images.unsplash.com/photo-1528819622761-6bcf002c2d8d?auto=format&fit=crop&w=900&q=80',
            'video_url': 'https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.webm',
            'rating': 4.6,
            'reviews_count': 86,
            'release_year': 2024,
        },
        {
            'title': 'Grid Empire',
            'description': 'Build, expand, and dominate a neon empire of strategic resources.',
            'category': 'Strategy',
            'download_link': 'https://store.steampowered.com/search/?term=Grid+Empire',
            'affiliate_link': 'https://store.steampowered.com/search/?term=Grid+Empire',
            'store_name': 'Steam',
            'image_url': 'https://images.unsplash.com/photo-1550745165-9bc0b252726f?auto=format&fit=crop&w=900&q=80',
            'video_url': 'https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4',
            'rating': 4.8,
            'reviews_count': 102,
            'release_year': 2025,
        },
        {
            'title': 'Turbo Arena',
            'description': 'A fast-paced sports battle with futuristic vehicles and skill boosts.',
            'category': 'Sports',
            'download_link': 'https://store.epicgames.com/en-US/browse?sortBy=relevancy&sortDir=DESC&keywords=Turbo%20Arena',
            'affiliate_link': 'https://store.epicgames.com/en-US/browse?sortBy=relevancy&sortDir=DESC&keywords=Turbo%20Arena',
            'store_name': 'Epic',
            'image_url': 'https://images.unsplash.com/photo-1517649763962-0c623066013b?auto=format&fit=crop&w=900&q=80',
            'video_url': 'https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.webm',
            'rating': 4.7,
            'reviews_count': 74,
            'release_year': 2026,
        },
        {
            'title': 'FIFA 27',
            'description': 'A realistic football experience with new tactics, enhanced club systems, and sharp presentation.',
            'category': 'Sports',
            'download_link': 'https://store.epicgames.com/en-US/browse?sortBy=relevancy&sortDir=DESC&keywords=FIFA%2027',
            'affiliate_link': 'https://store.epicgames.com/en-US/browse?sortBy=relevancy&sortDir=DESC&keywords=FIFA%2027',
            'store_name': 'Epic',
            'image_url': 'https://images.unsplash.com/photo-1547347298-4074fc3086f0?auto=format&fit=crop&w=900&q=80',
            'video_url': 'https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4',
            'rating': 4.9,
            'reviews_count': 306,
            'release_year': 2026,
        },
    ]

    existing_titles = {game.title for game in Game.query.all()}
    for item in games:
        if item['title'] not in existing_titles:
            db.session.add(Game(**item))

    for game in Game.query.all():
        if not game.video_url:
            for item in games:
                if item['title'] == game.title and item.get('video_url'):
                    game.video_url = item['video_url']
                    break

    update_game_store_links()
    db.session.commit()


def seed_reviews():
    reviews = [
        {
            'title': 'A polished football sim with lots of depth',
            'author': 'Leo',
            'rating': 4.9,
            'excerpt': 'The release build feels complete and the new game modes make every match feel more strategic.'
        },
        {
            'title': 'Great speed and style',
            'author': 'Ava',
            'rating': 4.8,
            'excerpt': 'The tracks are thrilling, the nitro systems are satisfying, and the visuals stay crisp during high-speed races.'
        },
        {
            'title': 'Big adventure energy',
            'author': 'Milo',
            'rating': 4.9,
            'excerpt': 'Exploration feels rewarding and the story beats land with a strong fantasy atmosphere.'
        },
    ]

    existing_titles = {review.title for review in Review.query.all()}
    game_map = {game.title: game for game in Game.query.all()}

    for review in reviews:
        if review['title'] in existing_titles:
            continue

        game_for_review = None
        if review['title'] == 'A polished football sim with lots of depth':
            game_for_review = game_map.get('FIFA 27')
        elif review['title'] == 'Great speed and style':
            game_for_review = game_map.get('Neon Drift')
        elif review['title'] == 'Big adventure energy':
            game_for_review = game_map.get('Skyline Quest')

        if game_for_review is None:
            continue

        db.session.add(Review(game_id=game_for_review.id, **review))

    db.session.commit()


def seed_news():
    posts = [
        {
            'title': 'FIFA 27 release date: what to expect from the next football season',
            'slug': 'fifa-27-release-date-what-to-expect',
            'category': 'News',
            'excerpt': 'Fans are already tracking the FIFA 27 release date and the biggest gameplay upgrades coming to this year’s football experience.',
            'body': 'The FIFA 27 release date remains one of the most searched football gaming topics as fans wait for the next version of the franchise. Expect improved match flow, smarter AI, and a stronger focus on career progression, club identity, and new game modes. This guide rounds up the most discussed updates and what players should watch for ahead of launch.'
        },
        {
            'title': 'Top 10 sports games trending this month',
            'slug': 'top-10-sports-games-trending',
            'category': 'Trending',
            'excerpt': 'Racing, football, and arcade sports titles are dominating player picks as fans look for the best current releases.',
            'body': 'The current sports lineup is packed with high-energy titles that blend realism with style. From football simulations to futuristic arcade racers, these games are pulling attention for their replay value, visuals, and community engagement.'
        },
        {
            'title': 'Best game reviews for action and adventure fans',
            'slug': 'best-game-reviews-action-adventure',
            'category': 'Reviews',
            'excerpt': 'If you want strong recommendations, this roundup highlights the action and adventure picks with the highest ratings.',
            'body': 'Players are chasing titles with polished combat, engaging stories, and standout visual design. These reviews help narrow down the strongest options across a crowded gaming landscape.'
        },
    ]

    existing_slugs = {post.slug for post in NewsPost.query.all()}
    for item in posts:
        if item['slug'] not in existing_slugs:
            db.session.add(NewsPost(**item))

    db.session.commit()


with app.app_context():
    db.create_all()
    ensure_schema()
    seed_games()
    update_game_store_links()
    seed_reviews()
    seed_news()


@app.route('/newsletter/signup', methods=['POST'])
def newsletter_signup():
    email = request.form.get('email', '').strip().lower()
    if not email:
        return redirect(url_for('monetize', error='Please enter an email address.'))

    if '@' not in email:
        return redirect(url_for('monetize', error='Please enter a valid email address.'))

    existing = NewsletterSubscriber.query.filter_by(email=email).first()
    if not existing:
        db.session.add(NewsletterSubscriber(email=email))
        db.session.commit()

    return redirect(url_for('monetize', success='Thanks for joining the GamePulse newsletter!'))


@app.route('/checkout/stripe', methods=['POST'])
def stripe_checkout():
    stripe_secret_key = os.getenv('STRIPE_SECRET_KEY', '').strip()
    stripe_price_id = os.getenv('STRIPE_PRICE_ID', '').strip()

    if not stripe_secret_key or not stripe_price_id:
        return redirect(url_for('monetize', error='Stripe is not configured yet. Add STRIPE_SECRET_KEY and STRIPE_PRICE_ID to your environment variables.'))

    try:
        import stripe
    except Exception:
        return redirect(url_for('monetize', error='The stripe package is not installed yet.'))

    try:
        stripe.api_key = stripe_secret_key
        session = stripe.checkout.Session.create(
            mode='subscription',
            line_items=[{'price': stripe_price_id, 'quantity': 1}],
            success_url=url_for('monetize', _external=True) + '?stripe_success=1',
            cancel_url=url_for('monetize', _external=True) + '?stripe_canceled=1',
            metadata={'plan': 'premium-membership', 'site': 'gamepulse'}
        )
        return redirect(session.url, code=303)
    except Exception as exc:
        return redirect(url_for('monetize', error=f'Stripe checkout failed: {exc}'))


@app.route('/checkout/paypal', methods=['POST'])
def paypal_checkout():
    amount = request.form.get('amount', '19.00').strip() or '19.00'
    paypal_email = os.getenv('PAYPAL_EMAIL', 'your-paypal-email@example.com').strip()
    item_name = request.form.get('item_name', 'GamePulse Premium Membership').strip() or 'GamePulse Premium Membership'
    return_url = url_for('monetize', _external=True)

    params = {
        'cmd': '_xclick',
        'business': paypal_email,
        'item_name': item_name,
        'amount': amount,
        'currency_code': 'USD',
        'return': return_url,
        'cancel_return': return_url,
        'notify_url': return_url,
        'no_shipping': '1',
        'src': '1',
        'sra': '1',
    }
    query = urlencode(params)
    return redirect(f'https://www.paypal.com/cgi-bin/webscr?{query}', code=303)


@app.route('/')
def home():
    search_query = request.args.get('q', '').strip()
    selected_category = request.args.get('category', 'All')
    selected_rating = request.args.get('rating', 'All')
    games_query = Game.query

    if selected_category and selected_category.lower() != 'all':
        games_query = games_query.filter(Game.category.ilike(selected_category))

    if selected_rating and selected_rating.lower() != 'all':
        try:
            rating_value = float(selected_rating)
            games_query = games_query.filter(Game.rating >= rating_value)
        except ValueError:
            pass

    if search_query:
        games_query = games_query.filter(
            (Game.title.ilike(f'%{search_query}%')) |
            (Game.description.ilike(f'%{search_query}%')) |
            (Game.category.ilike(f'%{search_query}%'))
        )

    games = games_query.order_by(Game.rating.desc(), Game.id.desc()).all()
    categories = ['All', 'Action', 'Racing', 'Adventure', 'Strategy', 'Shooter', 'Sports']
    rating_filters = ['All', '4.5', '4.7', '4.9']
    top_games = Game.query.order_by(Game.rating.desc(), Game.id.desc()).limit(10).all()
    featured_reviews = Review.query.order_by(Review.created_at.desc()).limit(3).all()
    news_posts = NewsPost.query.order_by(NewsPost.published_at.desc()).limit(3).all()
    revenue_streams = get_revenue_streams()

    return render_template(
        'index.html',
        games=games,
        search_query=search_query,
        categories=categories,
        selected_category=selected_category,
        selected_rating=selected_rating,
        rating_filters=rating_filters,
        top_games=top_games,
        featured_reviews=featured_reviews,
        news_posts=news_posts,
        revenue_streams=revenue_streams,
    )


@app.route('/monetize')
def monetize():
    return render_template('monetize.html', revenue_streams=get_revenue_streams())


@app.route('/reviews')
def reviews():
    reviews = Review.query.order_by(Review.created_at.desc()).all()
    return render_template('reviews.html', reviews=reviews)


@app.route('/trending')
def trending():
    games = Game.query.order_by(Game.rating.desc(), Game.id.desc()).limit(10).all()
    return render_template('trending.html', games=games)


@app.route('/news')
def news():
    posts = NewsPost.query.order_by(NewsPost.published_at.desc()).all()
    return render_template('news.html', posts=posts)


@app.route('/compare-games')
def compare_games():
    all_games = Game.query.order_by(Game.title.asc()).all()
    left_game_id = request.args.get('left', str(all_games[0].id) if all_games else None)
    right_game_id = request.args.get('right', str(all_games[1].id) if len(all_games) > 1 else None)

    left_game = Game.query.get(int(left_game_id)) if left_game_id else None
    right_game = Game.query.get(int(right_game_id)) if right_game_id else None

    return render_template('compare_games.html', games=all_games, left_game=left_game, right_game=right_game)


@app.route('/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        password = request.form.get('password', '')
        if password == 'Nanayaw1@2008':
            session['admin_logged_in'] = True
            return redirect(url_for('admin'))
        return render_template('login.html', error='Incorrect password. Please try again.')

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()

        error = None
        if not username or not email or not password:
            error = 'All fields are required.'
        elif len(password) < 6:
            error = 'Password must be at least 6 characters long.'
        elif password != confirm_password:
            error = 'Passwords do not match.'
        elif User.query.filter_by(username=username).first():
            error = 'Username already exists.'
        elif User.query.filter_by(email=email).first():
            error = 'Email already in use.'

        if error:
            return render_template('register.html', error=error)

        new_user = User(username=username, email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        session['user_logged_in'] = True
        session['user_id'] = new_user.id
        session['username'] = new_user.username
        return redirect(url_for('home'))

    return render_template('register.html')


@app.route('/user/login', methods=['GET', 'POST'])
def user_login():
    if request.method == 'POST':
        username_or_email = request.form.get('username_or_email', '').strip()
        password = request.form.get('password', '').strip()

        user = User.query.filter(
            (User.username == username_or_email) | (User.email == username_or_email)
        ).first()

        if user and user.check_password(password):
            session['user_logged_in'] = True
            session['user_id'] = user.id
            session['username'] = user.username
            return redirect(url_for('home'))

        return render_template('user_login.html', error='Invalid username/email or password.')

    return render_template('user_login.html')


@app.route('/user/logout')
def user_logout():
    session.pop('user_logged_in', None)
    session.pop('user_id', None)
    session.pop('username', None)
    return redirect(url_for('home'))


@app.route('/profile/<username>')
def view_profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    favorite_games = []
    if user.favorite_games:
        game_ids = [int(id.strip()) for id in user.favorite_games.split(',') if id.strip()]
        favorite_games = Game.query.filter(Game.id.in_(game_ids)).all()
    
    return render_template('profile.html', user=user, favorite_games=favorite_games)


@app.route('/profile/edit', methods=['GET', 'POST'])
@user_login_required
def edit_profile():
    user = User.query.get_or_404(session.get('user_id'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        bio = request.form.get('bio', '').strip()
        profile_image = request.form.get('profile_image', '').strip()

        # Check if username/email already taken by another user
        if username != user.username and User.query.filter_by(username=username).first():
            return render_template('edit_profile.html', user=user, error='Username already taken.')
        
        if email != user.email and User.query.filter_by(email=email).first():
            return render_template('edit_profile.html', user=user, error='Email already in use.')

        user.username = username or user.username
        user.email = email or user.email
        user.bio = bio
        user.profile_image = profile_image or 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=400&q=80'
        
        db.session.commit()
        session['username'] = user.username
        
        return redirect(url_for('view_profile', username=user.username))

    return render_template('edit_profile.html', user=user)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('admin_login'))


@app.route('/admin', methods=['GET', 'POST'])
@admin_login_required
def admin():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('desc', '').strip()
        link = request.form.get('link', '').strip()
        image = request.form.get('img', '').strip()
        video = request.form.get('video', '').strip()
        category = request.form.get('category', 'Action').strip()

        if not title or not link:
            return redirect(url_for('admin'))

        store_type = request.form.get('store_type', '').strip().lower() or 'store'
        store_name = request.form.get('store_name', '').strip() or store_type.title() or 'Store'
        affiliate_link = request.form.get('affiliate_link', '').strip() or link

        if not affiliate_link or affiliate_link == link:
            affiliate_link = build_affiliate_url(link, title, store_name)

        new_game = Game(
            title=title,
            description=description or 'New cyber game added to the archive.',
            category=category,
            download_link=link,
            affiliate_link=affiliate_link,
            store_name=store_name,
            store_type=store_type,
            image_url=image or 'https://images.unsplash.com/photo-1511512578047-dfb367046420?auto=format&fit=crop&w=900&q=80',
            video_url=video or None
        )
        db.session.add(new_game)
        db.session.commit()
        return redirect(url_for('admin'))

    games = Game.query.order_by(Game.id.desc()).all()
    return render_template('admin.html', games=games)


@app.route('/delete/<int:id>')
@admin_login_required
def delete_game(id):
    game_to_delete = Game.query.get_or_404(id)
    db.session.delete(game_to_delete)
    db.session.commit()
    return redirect(url_for('admin'))


@app.route('/sitemap.xml')
def sitemap():
    return send_file('static/sitemap.xml', mimetype='text/xml')


@app.route('/robots.txt')
def robots():
    return send_file('static/robots.txt', mimetype='text/plain')


if __name__ == '__main__':
    # Development only - Production uses Gunicorn
    app.run(debug=os.getenv('FLASK_ENV') == 'development', host='0.0.0.0', port=int(os.getenv('PORT', 5000)))