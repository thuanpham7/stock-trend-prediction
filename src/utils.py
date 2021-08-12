import math as m
import numpy as np
from sklearn.linear_model import LinearRegression

def search(form):
    if form["type"] == "basic":
        return basic_search(form)
    else:
        return trend_search(form)


def basic_search(form):
    query = "SELECT * from Company "

    # This block initializes a query to allow dynamically build the rest
    if form["companySymbol"]:
        query += "WHERE company_symbol = '%s' " % form["companySymbol"].upper()
    else:
        query += "WHERE company_symbol is not null "

    if form["indexSymbol"]:
        query += "AND index_symbol = '%s' " % form["indexSymbol"].upper()

    if form["sector"] != "*":
        query += "AND sector = '%s' " % form["sector"]

    if form["industry"] != "*":
        query += "AND industry = '%s' " % form["industry"]

    if form["marketCap"]:
        if form["price-option-mc"] == "GT":
            query += "AND market_cap > %d " % (float(form["marketCap"]) * 1000000000)
        else:
            query += "AND market_cap < %d " % (float(form["marketCap"]) * 1000000000)

    if form["pm"]:
        if form["price-option-pm"] == "GT":
            query += "AND profit_margin > %d " % float(form["pm"])
        else:
            query += "AND profit_margin < %d " % float(form["pm"])

    if form["dps"]:
        if form["price-option-dps"] == "GT":
            query += "AND dividend_per_share > %d " % float(form["dps"])
        else:
            query += "AND dividend_per_share < %d " % float(form["dps"])

    cursor = oracle_connection()
    cursor.execute(query)
    results = cursor.fetchall()
    final_query = f"""
    select *
    from quarterly_earning_report q, stock s, company c
    where q.end_date = (
        select max(end_date)
        from quarterly_earning_report
        where end_date <= to_date('2020-12-31', 'YYYY-MM-DD'))
    and  s.price_date = (
        select max(price_date)
        from stock
        where price_date <= to_date('2020-12-31', 'YYYY-MM-DD'))
    and q.company_symbol = s.company_symbol
    and q.company_symbol = c.company_symbol
    order by q.company_symbol
    """
    cursor.execute(final_query)
    all_companies = cursor.fetchall()

    searched_companies = [result[0] for result in results]
    return [company for company in all_companies if company[0] in searched_companies]


def trend_search(form):
    start_date = form["start"]
    end_date = form["end"]
    cursor = oracle_connection()
    final_results = []

    if form["qer-change"]:
        change = float(form["qer-change"])
        query = """
        select company_symbol, reported_eps 
            from quarterly_earning_report
            where start_date =( 
                select min(start_date) 
                from quarterly_earning_report 
                where start_date >= to_date('%s', 'YYYY-MM-DD'))
            or end_date = ( 
                select max(end_date) 
                from quarterly_earning_report 
                where end_date <= to_date('%s', 'YYYY-MM-DD')) 
            order by company_symbol, start_date""" % (
            start_date,
            end_date,
        )
        cursor.execute(query)

        results = cursor.fetchall()
        for i in range(len(results) - 2):
            if results[i][0] != results[i + 1][0]:
                continue

            if not results[i][1] or not results[i + 1][1]:
                continue

            start_value = results[i][1]
            end_value = results[i + 1][1]

            if form["qer-change-type"] == "percent":

                percent_change = ((end_value - start_value) / start_value) * 100
                if percent_change >= change:
                    final_results.append(results[i][0])

            else:
                value_change = end_value - start_value
                if value_change >= m.fabs:
                    final_results.append(results[i][0])

    if form["rve-change"]:
        change = float(form["rve-change"])
        if form["rve-change-type"] == "percent":
            print("percent")
            query = """
            select company_symbol from quarterly_earning_report 
            where end_date = (
                 select max(end_date) 
                 from quarterly_earning_report 
                 where end_date <= to_date('%s', 'YYYY-MM-DD')) 
                 and ((reported_eps - estimated_eps) / reported_eps) * 100 > %d 
            """ % (
                start_date,
                change,
            )
        else:
            query = """
            select company_symbol from quarterly_earning_report 
            where end_date = (
                 select max(end_date) 
                 from quarterly_earning_report 
                 where end_date <= to_date('%s', 'YYYY-MM-DD')) 
                 and (reported_eps - estimated_eps) > %d 
            """ % (
                end_date,
                change,
            )

        cursor.execute(query)
        results = cursor.fetchall()
        if final_results:
            for result in results:
                if result not in final_results:
                    final_results.remove(result[0])
        else:
            final_results = [result[0] for result in results]

    if form["price-change"]:
        change = float(form["price-change"])
        query = """
        select company_symbol, share_close 
            from stock
            where price_date =( 
                select min(price_date) 
                from stock 
                where price_Date >= to_date('%s', 'YYYY-MM-DD'))
            or price_date = ( 
                select max(price_date) 
                from stock 
                where price_date <= to_date('%s', 'YYYY-MM-DD')) 
            order by company_symbol, price_date""" % (
            start_date,
            end_date,
        )
        cursor.execute(query)

        results = cursor.fetchall()
        interm_results = []
        for i in range(len(results) - 2):
            if results[i][0] != results[i + 1][0]:
                continue

            if not results[i][1] or not results[i + 1][1]:
                continue

            start_value = results[i][1]
            end_value = results[i + 1][1]

            if form["qer-change-type"] == "percent":

                percent_change = ((end_value - start_value) / start_value) * 100
                if percent_change >= change:
                    interm_results.append(results[i][0])

            else:
                value_change = end_value - start_value
                if value_change >= m.fabs:
                    interm_results.append(results[i][0])

        if final_results:
            for result in interm_results:
                if result not in final_results:
                    final_results.remove(result[i][0])
        else:
            final_results = [result for result in interm_results]

    if form["volume-change"]:
        query = """
        select company_symbol, average_volume 
        from (
            select company_symbol, AVG(volume) as average_volume 
            from STOCK 
            where price_date >= to_date('%s', 'YYYY-MM-DD') 
            and price_date <= to_date('%s', 'YYYY-MM-DD') 
            group by company_symbol
        ) 
        where average_volume %s %d
        """ % (
            start_date,
            end_date,
            form["volume-direction"],
            float(form["volume-change"]) * 1000000,
        )

        cursor.execute(query)
        results = cursor.fetchall()
        if final_results:
            for result in results:
                if result not in final_results:
                    final_results.remove(result)
        else:
            final_results = results

    if form["volatility-change"]:
        query = """
        select company_symbol, average_volatility 
        from (
            select company_symbol, AVG(((share_high - share_low) / share_low) * 100) as average_volatility 
            from STOCK 
            where price_date >= to_date('%s', 'YYYY-MM-DD') 
            and price_date <= to_date('%s', 'YYYY-MM-DD') 
            group by company_symbol
        ) 
        where average_volatility %s %d
        """ % (
            start_date,
            end_date,
            form["volatility-direction"],
            float(form["volatility-change"]),
        )

        cursor.execute(query)
        results = cursor.fetchall()
        if final_results:
            for result in results:
                if result not in final_results:
                    final_results.remove(result)
        else:
            final_results = results

    final_query = f"""
    select *
    from quarterly_earning_report q, stock s, company c
    where q.end_date = (
        select max(end_date)
        from quarterly_earning_report
        where end_date <= to_date('{end_date}', 'YYYY-MM-DD'))
    and  s.price_date = (
        select max(price_date)
        from stock
        where price_date <= to_date('{end_date}', 'YYYY-MM-DD'))
    and q.company_symbol = s.company_symbol
    and q.company_symbol = c.company_symbol
    order by q.company_symbol
    """
    cursor.execute(final_query)
    all_companies = cursor.fetchall()
    return [company for company in all_companies if company[0] in final_results]


def get_data(symbol, type="share_close"):
    query = f"""
    select price_date, {type} 
    from stock 
    where company_symbol = '{symbol}'
    """
    cursor = oracle_connection()
    cursor.execute(query)
    return cursor.fetchall()


def get_moving_average(period, stock, type="SHARE_CLOSE"):
    query = f"""
    SELECT PRICE_DATE, SUM({type}) as total,
       AVG(SUM({type})) OVER
          (ORDER BY PRICE_DATE ROWS BETWEEN {period} PRECEDING AND CURRENT ROW) AS moving_average
    FROM STOCK
    where company_symbol = '{stock}'
    GROUP BY PRICE_DATE
    ORDER BY PRICE_DATE
    """

    cursor = oracle_connection()
    cursor.execute(query)
    moving_averages = cursor.fetchall()
    return [average[2] for average in moving_averages]


def fetch_initial_results():
    cursor = oracle_connection()
    final_query = f"""
    select *
    from quarterly_earning_report q, stock s, company c
    where q.end_date = (
        select max(end_date)
        from quarterly_earning_report
        where end_date <= to_date('2020-12-31', 'YYYY-MM-DD'))
    and  s.price_date = (
        select max(price_date)
        from stock
        where price_date <= to_date('2020-12-31', 'YYYY-MM-DD'))
    and q.company_symbol = s.company_symbol
    and q.company_symbol = c.company_symbol
    order by q.company_symbol
    """
    cursor.execute(final_query)
    all_companies = cursor.fetchall()
    return all_companies


def fetch_industries():
    cursor = oracle_connection()
    query = "SELECT industry FROM Company group by industry"
    cursor.execute(query)
    results = cursor.fetchall()
    cursor.close()
    return [result[0] for result in results]


def fetch_sectors():
    cursor = oracle_connection()
    query = "SELECT sector FROM Company group by sector"
    cursor.execute(query)

    results = cursor.fetchall()
    cursor.close()
    return [result[0] for result in results]

def fetch_earnings(stock):
    cursor = oracle_connection()
    query = "SELECT reported_EPS FROM Quarterly_Earning_Report WHERE company_symbol = \'" + stock + "\' ORDER BY end_date ASC FETCH FIRST 1 ROWS ONLY"
    cursor.execute(query)

    results = cursor.fetchall()
    cursor.close()

    return results[0][0]

def fetch_pred_earnings(stock):
    cursor = oracle_connection()
    query = "SELECT * FROM Quarterly_Earning_Report WHERE company_symbol = \'" + stock + "\'"
    cursor.execute(query)

    results = cursor.fetchall()
    cursor.close()

    indices = [(len(results) - x) for x in range(0, len(results))]
    eps = [result[3] for result in results]
    
    x = np.array(indices).reshape((-1, 1))
    y = np.array(eps)

    model = LinearRegression().fit(x, y)

    return (model.coef_ * (len(results) + 1) + model.intercept_)[0]

def fetch_price(stock):
    cursor = oracle_connection()
    query = "SELECT share_close FROM Stock WHERE company_symbol = \'" + stock + "\' ORDER BY price_date DESC FETCH FIRST 1 ROWS ONLY"
    cursor.execute(query)

    results = cursor.fetchall()
    cursor.close()

    return results[0][0]

def fetch_pred_price(stock):
    cursor = oracle_connection()
    query = "SELECT * FROM Stock WHERE company_symbol = \'" + stock + "\' ORDER BY price_date DESC"
    cursor.execute(query)

    results = cursor.fetchall()
    cursor.close()

    indices = [(len(results) - x) for x in range(0, len(results))]
    prices = [result[5] for result in results]
    
    print(indices[0])
    print(prices[0])
    x = np.array(indices).reshape((-1, 1))
    y = np.array(prices)

    model = LinearRegression().fit(x, y)
    print(model.intercept_)
    print(model.coef_)

    return (model.coef_ * (len(results) + 91) + model.intercept_)[0]

def eps_trend(stock):
    cursor = oracle_connection()
    query = f"SELECT reported_eps,estimated_eps, (reported_eps - estimated_eps) / estimated_eps,end_date FROM quarterly_earning_report WHERE company_symbol='{stock}'"
    cursor.execute(query)
    results = cursor.fetchall()
    cursor.close()
    return results
