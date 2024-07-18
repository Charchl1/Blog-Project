from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, URL, Email
from flask_ckeditor import CKEditor, CKEditorField


# ------- CREATE WTFORM ------- #
class CreatePostForm(FlaskForm):
    title = StringField('Blog Post Title', validators=[DataRequired()])
    subtitle = StringField('Blog Post Subtitle', validators=[DataRequired()])
    author_name = StringField("Author's name", validators=[DataRequired()])
    bg_img_url = StringField('Blog Image URL', validators=[DataRequired(), URL()])
    body = CKEditorField('Blog Content', validators=[DataRequired()])
    submit = SubmitField('Make post')


class RegisterForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired()])
    password = StringField('Password', validators=[DataRequired()])
    submit = SubmitField("Sign Up")


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired()])
    password = StringField('Password', validators=[DataRequired()])
    submit = SubmitField('Log In')


class CommentForm(FlaskForm):
    comment_field = CKEditorField('Comment', validators=[DataRequired()])
    submit_comment = SubmitField("Submit")
