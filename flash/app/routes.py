from flask import render_template
from app import app

@app.route('/')
@app.route('/index')
def index():
    user = {'username' : 'Gridley'}

    posts = [
        {
            'author': {'username': 'John'},
            'body': 'Beautiful day in Portland!'
        },
        {
            'author': {'username': 'Susan'},
            'body': 'The Avengers movie was so cool!'
        },
        {
            'author': {'username': 'Bill'},
            'body': 'The Tarzan movie was so dumb!'
        }
    ]

    return render_template('index.html', title='blogfog', user=user, posts=posts)
