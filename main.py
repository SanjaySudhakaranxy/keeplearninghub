from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('exams.html')

@app.route('/exams')
def exams():
    return render_template('exams.html')

@app.route('/results')
def results():
    return render_template('results.html')

@app.route('/about')
def about():
    return render_template('about.html')

if __name__ == '__main__':
    app.run(debug=True)
