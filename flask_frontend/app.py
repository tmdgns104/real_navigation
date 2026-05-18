from flask import Flask, render_template


app = Flask(__name__)


@app.route("/")
@app.route("/map")
def map_view():
    return render_template("map.html")


if __name__ == "__main__":
    app.run(host="127.0.0.1", debug=False, port=5000)
