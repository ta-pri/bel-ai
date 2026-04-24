from flask import Blueprint, render_template, request, abort, jsonify, session, redirect, url_for, current_app
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
from . import db
from .models import Book, User, Request
import os
 
main = Blueprint('main', __name__)
 
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
 
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
 
def save_cover(file):
    if file and file.filename and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
        filename = timestamp + filename
        upload_folder = current_app.config['UPLOAD_FOLDER']
        os.makedirs(upload_folder, exist_ok=True)
        file.save(os.path.join(upload_folder, filename))
        return f'/static/uploads/{filename}'
    return None
 
# ─── PUBLIC ──────────────────────────────────────────────────────────────────
 
@main.route('/')
def index():
    new_books = Book.query.filter_by(is_new=True).order_by(Book.created_at.desc()).limit(6).all()
    sale_books = Book.query.filter_by(is_sale=True).order_by(Book.created_at.desc()).limit(6).all()
    seasonal_books = Book.query.filter_by(is_seasonal=True).order_by(Book.created_at.desc()).limit(6).all()
    total = Book.query.count()
    return render_template('index.html',
                           new_books=new_books,
                           sale_books=sale_books,
                           seasonal_books=seasonal_books,
                           total=total)
 
@main.route('/catalog')
def catalog():
    return render_template('catalog.html')
 
@main.route('/book/<int:id>')
def book_detail(id):
    book = Book.query.get_or_404(id)
    related = Book.query.filter(
        Book.author == book.author, Book.id != book.id
    ).limit(4).all()
    return render_template('book_detail.html', book=book, related=related)
 
@main.route('/request', methods=['POST'])
def submit_request():
    data = request.get_json()
    req = Request(
        name=data.get('name', ''),
        phone=data.get('phone', ''),
        email=data.get('email', ''),
        message=data.get('message', ''),
        book_id=data.get('book_id') or None
    )
    db.session.add(req)
    db.session.commit()
    return jsonify({'success': True})
 
# ─── API ─────────────────────────────────────────────────────────────────────
 
@main.route('/api/books')
def api_books():
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)
    
    q = Book.query
    
    title = request.args.get('title', '')
    author = request.args.get('author', '')
    publisher = request.args.get('publisher', '')
    genre = request.args.get('genre', '')
    min_pages = request.args.get('min_pages', type=int)
    max_pages = request.args.get('max_pages', type=int)
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    is_new = request.args.get('is_new')
    is_sale = request.args.get('is_sale')
    is_seasonal = request.args.get('is_seasonal')
    sort_by = request.args.get('sort_by', 'created_at')
    sort_dir = request.args.get('sort_dir', 'desc')
    
    if title:
        q = q.filter(Book.title.ilike(f'%{title}%'))
    if author:
        q = q.filter(Book.author.ilike(f'%{author}%'))
    if publisher:
        q = q.filter(Book.publisher.ilike(f'%{publisher}%'))
    if genre:
        q = q.filter(Book.genre.ilike(f'%{genre}%'))
    if min_pages:
        q = q.filter(Book.pages >= min_pages)
    if max_pages:
        q = q.filter(Book.pages <= max_pages)
    if min_price is not None:
        q = q.filter(Book.price >= min_price)
    if max_price is not None:
        q = q.filter(Book.price <= max_price)
    if is_new == 'true':
        q = q.filter(Book.is_new == True)
    if is_sale == 'true':
        q = q.filter(Book.is_sale == True)
    if is_seasonal == 'true':
        q = q.filter(Book.is_seasonal == True)
    
    sort_col_map = {
        'title': Book.title,
        'author': Book.author,
        'pages': Book.pages,
        'price': Book.price,
        'year': Book.year,
        'created_at': Book.created_at,
    }
    sort_col = sort_col_map.get(sort_by, Book.created_at)
    if sort_dir == 'desc':
        q = q.order_by(sort_col.desc())
    else:
        q = q.order_by(sort_col.asc())
    
    total = q.count()
    books = q.offset((page - 1) * limit).limit(limit).all()
    
    return jsonify({
        'books': [b.to_dict() for b in books],
        'total': total,
        'page': page,
        'pages_total': max(1, (total + limit - 1) // limit)
    })
 
@main.route('/api/genres')
def api_genres():
    genres = db.session.query(Book.genre).distinct().filter(Book.genre != '').all()
    return jsonify([g[0] for g in genres if g[0]])
 
# ─── AUTH ─────────────────────────────────────────────────────────────────────
 
@main.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login_val = request.form.get('login')
        password = request.form.get('password')
        user = User.query.filter_by(login=login_val).first()
        if user and check_password_hash(user.password, password):
            session['admin'] = True
            return redirect(url_for('main.admin'))
        return render_template('login.html', error='Неверный логин или пароль')
    return render_template('login.html')
 
@main.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect(url_for('main.index'))
 
# ─── ADMIN ────────────────────────────────────────────────────────────────────
 
def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin'):
            return redirect(url_for('main.login'))
        return f(*args, **kwargs)
    return decorated
 
@main.route('/admin')
@admin_required
def admin():
    search = request.args.get('q', '')
    q = Book.query
    if search:
        q = q.filter(
            db.or_(Book.title.ilike(f'%{search}%'), Book.author.ilike(f'%{search}%'))
        )
    books = q.order_by(Book.id.desc()).all()
    unread_requests = Request.query.filter_by(is_read=False).count()
    return render_template('admin.html', books=books, search=search, unread=unread_requests)
 
@main.route('/admin/add', methods=['GET', 'POST'])
@admin_required
def admin_add():
    if request.method == 'POST':
        cover_url = save_cover(request.files.get('cover')) or '/static/img/book_placeholder.jpg'
        def safe_int(val, default=0):
            try: return int(val) if val and str(val).strip() else default
            except (ValueError, TypeError): return default
 
        def safe_float(val, default=0.0):
            try: return float(val) if val and str(val).strip() else default
            except (ValueError, TypeError): return default
 
        book = Book(
            title=request.form.get('title'),
            author=request.form.get('author'),
            pages=safe_int(request.form.get('pages'), 0),
            publisher=request.form.get('publisher'),
            description=request.form.get('description', ''),
            price=safe_float(request.form.get('price'), 0.0),
            genre=request.form.get('genre', ''),
            year=safe_int(request.form.get('year'), 2024),
            is_new=bool(request.form.get('is_new')),
            is_sale=bool(request.form.get('is_sale')),
            sale_percent=safe_int(request.form.get('sale_percent'), 0),
            is_seasonal=bool(request.form.get('is_seasonal')),
            cover_url=cover_url
        )
        db.session.add(book)
        db.session.commit()
        return redirect(url_for('main.admin'))
    return render_template('admin_form.html', book=None, action='add')
 
@main.route('/admin/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
def admin_edit(id):
    book = Book.query.get_or_404(id)
    if request.method == 'POST':
        new_cover = save_cover(request.files.get('cover'))
        book.title = request.form.get('title')
        book.author = request.form.get('author')
        def safe_int(val, default=0):
            try: return int(val) if val and str(val).strip() else default
            except (ValueError, TypeError): return default
 
        def safe_float(val, default=0.0):
            try: return float(val) if val and str(val).strip() else default
            except (ValueError, TypeError): return default
 
        book.pages = safe_int(request.form.get('pages'), 0)
        book.publisher = request.form.get('publisher')
        book.description = request.form.get('description', '')
        book.price = safe_float(request.form.get('price'), 0.0)
        book.genre = request.form.get('genre', '')
        book.year = safe_int(request.form.get('year'), 2024)
        book.is_new = bool(request.form.get('is_new'))
        book.is_sale = bool(request.form.get('is_sale'))
        book.sale_percent = safe_int(request.form.get('sale_percent'), 0)
        book.is_seasonal = bool(request.form.get('is_seasonal'))
        if new_cover:
            book.cover_url = new_cover
        db.session.commit()
        return redirect(url_for('main.admin'))
    return render_template('admin_form.html', book=book, action='edit')
 
@main.route('/admin/delete/<int:id>', methods=['POST'])
@admin_required
def admin_delete(id):
    book = Book.query.get_or_404(id)
    db.session.delete(book)
    db.session.commit()
    return redirect(url_for('main.admin'))
 
@main.route('/admin/requests')
@admin_required
def admin_requests():
    reqs = Request.query.order_by(Request.created_at.desc()).all()
    for r in reqs:
        if not r.is_read:
            r.is_read = True
    db.session.commit()
    return render_template('admin_requests.html', requests=reqs)
 
@main.route('/admin/init')
@main.route('/admin/init')
@admin_required
def init_db():
    Book.query.delete()
    db.session.commit()
 
    # Обложки с Open Library Covers API — бесплатно, без ключа
    # Если интернет недоступен — подставится placeholder автоматически (onerror в шаблоне)
    sample_books = [
        {
            "title": "Мастер и Маргарита", "author": "М. Булгаков",
            "pages": 480, "publisher": "Азбука", "genre": "Классика",
            "price": 590, "year": 1967, "is_new": False, "is_sale": True, "sale_percent": 20, "is_seasonal": False,
            "cover_url": "https://covers.openlibrary.org/b/isbn/9785389073906-L.jpg",
            "description": "Один из величайших романов русской литературы, сочетающий мистику, сатиру и глубокую философию."
        },
        {
            "title": "Преступление и наказание", "author": "Ф. Достоевский",
            "pages": 672, "publisher": "Эксмо", "genre": "Классика",
            "price": 450, "year": 1866, "is_new": False, "is_sale": False, "sale_percent": 0, "is_seasonal": False,
            "cover_url": "https://covers.openlibrary.org/b/isbn/9785699217144-L.jpg",
            "description": "Психологический триллер о преступлении и душевных муках человека, преступившего закон."
        },
        {
            "title": "Война и мир", "author": "Л. Толстой",
            "pages": 1274, "publisher": "АСТ", "genre": "Классика",
            "price": 780, "year": 1869, "is_new": False, "is_sale": False, "sale_percent": 0, "is_seasonal": True,
            "cover_url": "https://covers.openlibrary.org/b/isbn/9785170839407-L.jpg",
            "description": "Эпическая сага о войне, любви и судьбах людей в переломное время истории России."
        },
        {
            "title": "1984", "author": "Дж. Оруэлл",
            "pages": 320, "publisher": "АСТ", "genre": "Фантастика",
            "price": 420, "year": 1949, "is_new": True, "is_sale": False, "sale_percent": 0, "is_seasonal": False,
            "cover_url": "https://covers.openlibrary.org/b/isbn/9780451524935-L.jpg",
            "description": "Антиутопия о тоталитарном обществе будущего, где Старший Брат следит за каждым."
        },
        {
            "title": "Пикник на обочине", "author": "Братья Стругацкие",
            "pages": 256, "publisher": "АСТ", "genre": "Фантастика",
            "price": 380, "year": 1972, "is_new": True, "is_sale": True, "sale_percent": 15, "is_seasonal": False,
            "cover_url": "https://covers.openlibrary.org/b/isbn/9785170537808-L.jpg",
            "description": "Научно-фантастическая повесть о Зоне — месте странного и опасного инопланетного присутствия."
        },
        {
            "title": "Братья Карамазовы", "author": "Ф. Достоевский",
            "pages": 992, "publisher": "Эксмо", "genre": "Классика",
            "price": 650, "year": 1880, "is_new": False, "is_sale": False, "sale_percent": 0, "is_seasonal": False,
            "cover_url": "https://covers.openlibrary.org/b/isbn/9785040913541-L.jpg",
            "description": "Последний и самый масштабный роман Достоевского о семье, вере и нравственности."
        },
        {
            "title": "Трудно быть богом", "author": "Братья Стругацкие",
            "pages": 224, "publisher": "Азбука", "genre": "Фантастика",
            "price": 350, "year": 1964, "is_new": True, "is_sale": False, "sale_percent": 0, "is_seasonal": False,
            "cover_url": "https://covers.openlibrary.org/b/isbn/9785389065536-L.jpg",
            "description": "Философская фантастика о благородном рыцаре, попавшем в общество, которое он пытается изменить."
        },
        {
            "title": "Гарри Поттер и философский камень", "author": "Дж. Роулинг",
            "pages": 432, "publisher": "Махаон", "genre": "Детская литература",
            "price": 690, "year": 1997, "is_new": False, "is_sale": True, "sale_percent": 30, "is_seasonal": True,
            "cover_url": "https://covers.openlibrary.org/b/isbn/9785389077690-L.jpg",
            "description": "Волшебная история о мальчике-волшебнике, положившая начало одной из самых известных серий книг."
        },
        {
            "title": "Алиса в Стране чудес", "author": "Л. Кэрролл",
            "pages": 180, "publisher": "Махаон", "genre": "Детская литература",
            "price": 320, "year": 1865, "is_new": False, "is_sale": False, "sale_percent": 0, "is_seasonal": True,
            "cover_url": "https://covers.openlibrary.org/b/isbn/9780141439761-L.jpg",
            "description": "Классическая сказка о девочке, попавшей в удивительный мир абсурда и чудес."
        },
        {
            "title": "Двенадцать стульев", "author": "И. Ильф, Е. Петров",
            "pages": 416, "publisher": "Азбука", "genre": "Классика",
            "price": 410, "year": 1928, "is_new": False, "is_sale": True, "sale_percent": 10, "is_seasonal": False,
            "cover_url": "https://covers.openlibrary.org/b/isbn/9785389046986-L.jpg",
            "description": "Остроумная сатира о поисках несуществующих сокровищ в советской России."
        },
        {
            "title": "Собачье сердце", "author": "М. Булгаков",
            "pages": 160, "publisher": "Азбука", "genre": "Классика",
            "price": 290, "year": 1925, "is_new": True, "is_sale": False, "sale_percent": 0, "is_seasonal": False,
            "cover_url": "https://covers.openlibrary.org/b/isbn/9785389051355-L.jpg",
            "description": "Философская повесть о том, что происходит, когда наука вмешивается в природу."
        },
        {
            "title": "Унесённые ветром", "author": "М. Митчелл",
            "pages": 1024, "publisher": "Эксмо", "genre": "Роман",
            "price": 820, "year": 1936, "is_new": False, "is_sale": False, "sale_percent": 0, "is_seasonal": True,
            "cover_url": "https://covers.openlibrary.org/b/isbn/9780743273565-L.jpg",
            "description": "Эпическая история любви на фоне Гражданской войны в Америке."
        },
        {
            "title": "Мёртвые души", "author": "Н. Гоголь",
            "pages": 352, "publisher": "АСТ", "genre": "Классика",
            "price": 330, "year": 1842, "is_new": False, "is_sale": True, "sale_percent": 25, "is_seasonal": False,
            "cover_url": "https://covers.openlibrary.org/b/isbn/9785170792269-L.jpg",
            "description": "Поэма в прозе о похождениях авантюриста Чичикова и галерее портретов русских помещиков."
        },
        {
            "title": "Отцы и дети", "author": "И. Тургенев",
            "pages": 288, "publisher": "Эксмо", "genre": "Классика",
            "price": 360, "year": 1862, "is_new": False, "is_sale": False, "sale_percent": 0, "is_seasonal": True,
            "cover_url": "https://covers.openlibrary.org/b/isbn/9785699219001-L.jpg",
            "description": "Роман о конфликте поколений и нигилизме на фоне пореформенной России."
        },
        {
            "title": "Анна Каренина", "author": "Л. Толстой",
            "pages": 864, "publisher": "Азбука", "genre": "Роман",
            "price": 680, "year": 1878, "is_new": True, "is_sale": False, "sale_percent": 0, "is_seasonal": False,
            "cover_url": "https://covers.openlibrary.org/b/isbn/9785389058576-L.jpg",
            "description": "История о любви, измене и трагической судьбе женщины в светском обществе царской России."
        },
        {
            "title": "Маленький принц", "author": "А. де Сент-Экзюпери",
            "pages": 112, "publisher": "Эксмо", "genre": "Детская литература",
            "price": 380, "year": 1943, "is_new": False, "is_sale": True, "sale_percent": 20, "is_seasonal": True,
            "cover_url": "https://covers.openlibrary.org/b/isbn/9780156012195-L.jpg",
            "description": "Философская сказка о маленьком принце, путешествующем по планетам в поисках смысла жизни."
        },
    ]
 
    for b in sample_books:
        book = Book(**b)
        db.session.add(book)
 
    db.session.commit()
    return redirect(url_for('main.admin'))
 