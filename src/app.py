from src.utils import (
    fetch_price,
    fetch_pred_price,
    fetch_pred_earnings,
    fetch_earnings,
    fetch_industries,
    fetch_initial_results,
    fetch_sectors,
    get_moving_average,
    get_data,
    search,
    eps_trend
)
from flask import Flask, render_template, request

app = Flask(__name__)


@app.route("/", methods=["POST", "GET"])
def homepage():
    if request.method == "POST":
        try:
            results = search(request.form)
        except Exception:
            results = []
        return render_template(
            "basic.html", sectors=fetch_sectors(), industries=fetch_industries(), results=results, form=request.form
        )

    initial_results = fetch_initial_results()
    return render_template(
        "basic.html", sectors=fetch_sectors(), industries=fetch_industries(), results=initial_results
    )


@app.route("/analyze/<stock>/", methods=["POST", "GET"])
def analyze(stock, slow_period=26, fast_period=14, volume_period=7):

    if request.method == "POST":
        slow_period = request.form["slow"]
        fast_period = request.form["fast"]
        volume_period = request.form["volume_period"]
    else:
        request.form = {"slow": slow_period, "fast": fast_period, "volume_period": volume_period}

    price_data = get_data(stock)
    dates = [data[0].strftime("%Y-%m-%d") for data in price_data]
    prices = [data[1] for data in price_data]
    short_price_moving_average = get_moving_average(period=fast_period, stock=stock)
    long_price_moving_average = get_moving_average(period=slow_period, stock=stock)

    volume_data = get_moving_average(period=volume_period, stock=stock, type="volume")
    volume_moving_average = get_moving_average(period=fast_period, stock=stock, type="volume")
    volatility_data = get_moving_average(period=volume_period, stock=stock, type="share_high - share_low")
    volatility_moving_average = get_moving_average(period=fast_period, stock=stock, type="share_high - share_low")

    eps_data = eps_trend(stock)
    eps_date = [data[3].strftime("%Y-%m-%d") for data in eps_data]
    eps_percent_change = [data[2] * 100 for data in eps_data]
    return render_template(
        "analyze.html",
        stock=stock,
        prices=prices,
        dates=dates,
        price_ma=short_price_moving_average,
        long_price_ma=long_price_moving_average,
        volumes=volume_data,
        volume_averages=volume_moving_average,
        volatilities=volatility_data,
        volatility_averages=volatility_moving_average,
        form=request.form,
        latest_earnings=fetch_earnings(stock),
        pred_earnings=fetch_pred_earnings(stock),
        latest_price=fetch_price(stock),
        pred_price=fetch_pred_price(stock),
        eps_percent_change=eps_percent_change,
        eps_date=eps_date
    )


@app.route("/compare-stocks/<stocks>/")
def compareStocks(stocks):
    return render_template("compare_table.html", stocks=stocks)
