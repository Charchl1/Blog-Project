import os
from functools import wraps
from flask_wtf.csrf import CSRFProtect
from flask import Flask, render_template, redirect, url_for, request, flash, abort
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, Text, ForeignKey
from datetime import date
from flask_ckeditor import CKEditor
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_gravatar import Gravatar

from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm

app = Flask(__name__)
SECRET_KEY = os.urandom(32)
app.config['SECRET_KEY'] = SECRET_KEY

csrf = CSRFProtect(app)
csrf.init_app(app)
app.config['WTF_CSRF_SECRET_KEY'] = SECRET_KEY

Bootstrap5(app)
ckeditor = CKEditor(app)

login_manager = LoginManager()
login_manager.init_app(app)

gravatar = Gravatar(app,
                    size=40,
                    rating='g',
                    default='identicon',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)


# ------- CREATE DATABASE ------- #
class Base(DeclarativeBase):
    pass


app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DB_URI", 'sqlite:///blog.db')
db = SQLAlchemy(model_class=Base, session_options={"autoflush": False})
db.init_app(app)


# ------- CONFIGURE TABLE ------- #
class BlogPost(db.Model):
    __tablename__ = "posts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # # Here is author_id is a key between two tables. It will get the current user's id
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    # # first argument is a parent table class name
    # # back_populates to the exact row in the parent table
    author = relationship("User", back_populates="posts")
    title: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    subtitle: Mapped[str] = mapped_column(String(250), nullable=False)
    date: Mapped[str] = mapped_column(String(250), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    img_url: Mapped[str] = mapped_column(String(250), nullable=False)
    # # Relation to Comment
    comments = relationship("Comment", back_populates="parent_post")


class Comment(db.Model):
    __tablename__ = "comments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    # # Relation to User
    comment_author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    comment_author = relationship("User", back_populates="comments")
    # # Relation to BlogPost
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id"))
    parent_post = relationship("BlogPost", back_populates="comments")


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(100), unique=False, nullable=False)
    name: Mapped[str] = mapped_column(String(250), unique=False, nullable=False)
    # # relationship One User to Many BlogPosts
    # # so first argument is the class name of child table
    # # back_populates to the row in child table
    posts = relationship("BlogPost", back_populates="author")
    # # Relation to Comment
    comments = relationship("Comment", back_populates="comment_author")

    def is_active(self):
        return True

    def is_authenticated(self):
        return True

    def is_anonymous(self):
        return False


with app.app_context():
    db.create_all()

def admin_only(function):
    @wraps(function)
    @login_required
    def decorated_function(*args, **kwargs):
        if current_user.id != 1:
            return abort(403)
        return function(*args, **kwargs)
    return decorated_function


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)


@app.route('/clean-blog')
def get_all_posts():
    posts = []
    db_posts = db.session.execute(db.select(BlogPost).order_by(BlogPost.id)).scalars().all()
    for i in db_posts:
        posts.append(i)
    return render_template("index.html", all_posts=posts)


@app.route('/show-post/<int:post_id>', methods=["GET", "POST"])
def show_post(post_id):
    requested_post = db.session.execute(db.select(BlogPost).where(BlogPost.id == post_id)).scalar()

    comment_form = CommentForm()
    if current_user.is_authenticated:
        if comment_form.validate_on_submit():
            new_comment = Comment(text=request.form.get('comment_field'),
                                  comment_author=current_user,
                                  parent_post=requested_post)
            db.session.add(new_comment)
            db.session.commit()
    else:
        flash("In order to leave comments you should be Logged In.", "error")

    comments_list = []
    comments = db.session.execute(db.select(Comment).where(Comment.post_id == post_id)).scalars().all()
    for i in comments:
        comments_list.append(i)
    return render_template("post.html", post=requested_post, comment_form=comment_form,
                           comments=comments_list, current_user=current_user)


@app.route('/new-post', methods=["POST", "GET"])
@admin_only
def create_post():
    # ------- get understanding from which route we came to make-post.html ------- #
    rule = request.url_rule
    create = False
    if 'new-post' in rule.rule:
        create = True
    # ------- creating post ------- #
    post_date = date.today()
    create_post_form = CreatePostForm(author_name=current_user.name)
    if request.method == "POST" and create_post_form.validate_on_submit():
        with app.app_context():
            post_author = db.session.execute(db.select(User).where(User.name == request.form.get('author_name'))).scalar()
            author_id = post_author.id
            new_post = BlogPost(title=request.form.get('title'),
                                subtitle=request.form.get('subtitle'),
                                date=f"{post_date.strftime("%B")} {post_date.strftime("%d")},"
                                     f" {post_date.strftime("%Y")}",
                                body=request.form.get('body'),
                                author=post_author,
                                author_id=author_id,
                                img_url=request.form.get('bg_img_url'))
            db.session.add(new_post)
            db.session.commit()
        return redirect(url_for('get_all_posts'))
    return render_template('make-post.html', cr_form=create_post_form, check_route=create)


@app.route("/edit-post/<int:post_id>", methods=["POST", "GET"])
@admin_only
def edit_post(post_id):
    # ------- get understanding from which route we came to make-post.html ------- #
    rule = request.url_rule
    create = False
    if 'show-post' in rule.rule:
        create = True
    # ------ get current post ------- #
    current_post = db.session.execute(db.select(BlogPost).where(BlogPost.id == post_id)).scalar()
    # ------- connecting form to edit post ------- #
    # ------- filling the editing form with existing data ------- #
    edit_form = CreatePostForm(title=current_post.title,
                               subtitle=current_post.subtitle,
                               body=current_post.body,
                               author_name=current_user.name,
                               bg_img_url=current_post.img_url)
    # ------- accepting changes and updating post in the database ------- #
    post_author = db.session.execute(db.select(User).where(User.name == request.form.get('author_name'))).scalar()
    if request.method == "POST" and edit_form.validate_on_submit():
        current_post.title = request.form.get('title')
        current_post.subtitle = request.form.get('subtitle')
        current_post.body = request.form.get('body')
        current_post.author = post_author
        current_post.img_url = request.form.get('bg_img_url')
        db.session.commit()
        return redirect(url_for('show_post', post_id=post_id))
    return render_template("make-post.html", post_id=post_id, check_route=create,
                           post=current_post, cr_form=edit_form)


@app.route('/delete-post/<int:post_id>')
@admin_only
def delete_post(post_id):
    with app.app_context():
        post_to_delete = db.session.execute(db.select(BlogPost).where(BlogPost.id == post_id)).scalar()
        db.session.delete(post_to_delete)
        db.session.commit()
    return redirect(url_for('get_all_posts', post_id=post_id))


# Below is the code from previous lessons. No changes needed.
@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.route("/register", methods=["POST", "GET"])
def register():
    registration_form = RegisterForm()
    user_name = request.form.get('name')
    user_email = request.form.get('email')
    if request.method == "POST" and registration_form.validate_on_submit():
        if db.session.query(db.exists().where(User.email == user_email)).scalar():
            flash("You have already signed up with that email. Try to log in.", "error")
        else:
            new_user = User(email=user_email,
                            password=generate_password_hash(password=request.form.get('password'),
                                                            method="pbkdf2:sha256",
                                                            salt_length=8),
                            name=user_name)
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            return redirect(url_for("get_all_posts", username=user_name))
    return render_template("register.html", reg_form=registration_form)


@app.route("/login", methods=["POST", "GET"])
def login():
    login_form = LoginForm()
    user_email = request.form.get('email')
    user_password = request.form.get('password')
    user_to_login = db.session.execute(db.select(User).where(User.email == user_email)).scalar()
    if request.method == "POST" and login_form.validate_on_submit():
        if not user_to_login:
            flash("User with that email does not exist. Check your email or register.", "error")
        elif not check_password_hash(pwhash=user_to_login.password,
                                     password=user_password):
            flash("Wrong password.", "error")
        else:
            login_user(user_to_login)
            return redirect(url_for('get_all_posts', username=user_to_login.name))
    return render_template("login.html", login_form=login_form)


@app.route("/logout", methods=['POST', 'GET'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


if __name__ == "__main__":
    app.run(debug=False, port=5003)
