import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objs as go
import yfinance as yf
import pandas as pd
import numpy as np
from scipy.stats import norm
from datetime import datetime
import warnings

warnings.filterwarnings('ignore')

class OptionAnalyzer:
    def __init__(self, symbol='GLD'):
        self.symbol = symbol
        self.df = pd.DataFrame()

    def get_market_data(self):
        try:
            stock = yf.Ticker(self.symbol)
            # Prezzo spot affidabile
            spot_price = stock.info.get('currentPrice') or stock.history(period='2d')['Close'].iloc[-1]
            
            expirations = stock.options
            if not expirations:
                return None, None, None

            # Nearest expiry
            target_expiry = expirations[4]   # ← qui: [0] = nearest, [1] = 2nd, [2] = 3rd, [4] = 5th

            opt_chain = stock.option_chain(target_expiry)
            return spot_price, opt_chain, target_expiry
        
        except Exception as e:
            print(f"Errore recupero dati: {e}")
            return None, None, None

    def calculate_greeks(self, S, K, T_days, sigma, opt_type):
        if sigma <= 0 or T_days <= 0:
            return 0, 0
        T = T_days / 365.0
        r = 0.042  
        d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
        delta = norm.cdf(d1) if opt_type == 'C' else norm.cdf(d1) - 1
        gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
        return delta, gamma

    def process_data(self, spot_price, opt_chain, expiry):
        expiry_date = datetime.strptime(expiry, '%Y-%m-%d')
        remaining = expiry_date - datetime.now()
        T_days = max(remaining.total_seconds() / 86400.0, 0.01)
        data_list = []
        for opt_type, chain in [('C', opt_chain.calls), ('P', opt_chain.puts)]:
            for _, row in chain.iterrows():
                if pd.notnull(row['lastPrice']) and row['lastPrice'] > 0:
                    iv = row['impliedVolatility']
                    delta, gamma = self.calculate_greeks(spot_price, row['strike'], T_days, iv, opt_type)
                    data_list.append({
                        'strike': row['strike'],
                        'right': opt_type,
                        'last': row['lastPrice'],
                        'volume': row.get('volume', 0),
                        'oi': row.get('openInterest', 0),
                        'iv': iv,
                        'delta': delta,
                        'gamma': gamma,
                        'moneyness': row['strike'] / spot_price
                    })
        return pd.DataFrame(data_list)


# ────────────────────────────────────────────────
# Dash
# ────────────────────────────────────────────────
app = dash.Dash(__name__)

analyzer = OptionAnalyzer(symbol='SPY')   # ← change ticker here

app.layout = html.Div([
    html.H1(
        "Options Chain Live Dashboard",
        style={
            'textAlign': 'center',
            'color': '#58a6ff',
            'margin': '20px 0 10px 0',
            'fontFamily': 'Segoe UI, sans-serif'
        }
    ),

    html.Div(id='header-info', style={
        'textAlign': 'center',
        'color': '#8b949e',
        'fontSize': '18px',
        'marginBottom': '30px'
    }),

    # Row 1 – 3 grafici
    html.Div([
        html.Div(dcc.Graph(id='vol-skew'), style={'width': '33%', 'padding': '0 8px'}),
        html.Div(dcc.Graph(id='vol-smile'), style={'width': '33%', 'padding': '0 8px'}),
        html.Div(dcc.Graph(id='delta-profile'), style={'width': '33%', 'padding': '0 8px'}),
    ], style={'display': 'flex', 'marginBottom': '20px'}),

    # Row 2 – altri 3 grafici
    html.Div([
        html.Div(dcc.Graph(id='oi-profile'), style={'width': '33%', 'padding': '0 8px'}),
        html.Div(dcc.Graph(id='volume-profile'), style={'width': '33%', 'padding': '0 8px'}),
        html.Div(dcc.Graph(id='gamma-profile'), style={'width': '33%', 'padding': '0 8px'}),
    ], style={'display': 'flex'}),

    dcc.Interval(id='interval-component', interval=10*1000, n_intervals=0)  # update every 10 seconds

], style={
    'backgroundColor': '#0d1117',
    'color': '#c9d1d9',
    'padding': '20px',
    'minHeight': '100vh',
    'fontFamily': 'Segoe UI, -apple-system, BlinkMacSystemFont, sans-serif'
})


# ────────────────────────────────────────────────
# Live update callback
# ────────────────────────────────────────────────
@app.callback(
    [Output('vol-skew', 'figure'),
     Output('vol-smile', 'figure'),
     Output('delta-profile', 'figure'),
     Output('oi-profile', 'figure'),
     Output('volume-profile', 'figure'),
     Output('gamma-profile', 'figure'),
     Output('header-info', 'children')],
    Input('interval-component', 'n_intervals')
)
def update_dashboard(n):
    spot, chain, expiry = analyzer.get_market_data()
    if spot is None or chain is None:
        empty_fig = go.Figure()
        empty_fig.update_layout(template='plotly_dark')
        return [empty_fig] * 6 + ["Errore nel recupero dati da Yahoo Finance"]

    df = analyzer.process_data(spot, chain, expiry)
    analyzer.df = df

    vol_call = df[df['right'] == 'C']['volume'].sum()
    vol_put = df[df['right'] == 'P']['volume'].sum()
    pc_ratio = vol_put / vol_call if vol_call > 0 else 0

    view_low, view_high = spot * 0.94, spot * 1.06
    df_active = df[df['volume'] > 0].sort_values('strike')

    # Helper function for consistent dark theme styling
    def apply_dark_theme(fig, title):
        fig.update_layout(
            title=title,
            template='plotly_dark',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font_color='#c9d1d9',
            title_font_color='#58a6ff',
            legend_bgcolor='#161b22',
            legend_bordercolor='#30363d',
            margin=dict(l=40, r=40, t=60, b=40),
            xaxis=dict(
                gridcolor='#21262d',
                zerolinecolor='#21262d',
                title_font_color='#8b949e'
            ),
            yaxis=dict(
                gridcolor='#21262d',
                zerolinecolor='#21262d',
                title_font_color='#8b949e'
            )
        )
        return fig

    # 1. Volatility Skew
    skew = df_active.groupby('strike')['iv'].mean()
    fig_skew = go.Figure()
    fig_skew.add_trace(go.Scatter(x=skew.index, y=skew.values, mode='lines', line=dict(color='#58a6ff', width=2)))
    fig_skew.add_vline(x=spot, line_dash="dash", line_color='#f85149', annotation_text=f"Spot {spot:.2f}")
    fig_skew.update_layout(xaxis_range=[view_low, view_high])
    apply_dark_theme(fig_skew, 'Volatility Skew')

    # 2. Volatility Smile
    smile = df_active.groupby('moneyness')['iv'].mean()
    fig_smile = go.Figure()
    fig_smile.add_trace(go.Scatter(x=smile.index, y=smile.values, mode='lines', line=dict(color='#ffa657', width=2)))
    fig_smile.add_vline(x=1.0, line_dash="dot", line_color='#8b949e')
    fig_smile.update_layout(xaxis_range=[0.94, 1.06])
    apply_dark_theme(fig_smile, 'Volatility Smile')

    # 3. Delta Profile
    df_calls = df[df['right']=='C'].sort_values('strike')
    df_puts = df[df['right']=='P'].sort_values('strike')

    fig_delta = go.Figure()
    fig_delta.add_trace(go.Scatter(
        x=df_calls['strike'], y=df_calls['delta'],
        mode='lines+markers',  # line + dots
        line=dict(color='#2ecc71', width=2.5), 
        marker=dict(size=6, opacity=0.8),
        name='Calls'
    ))
    fig_delta.add_trace(go.Scatter(
        x=df_puts['strike'], y=df_puts['delta'],
        mode='lines+markers',
        line=dict(color='#e74c3c', width=2.5),
        marker=dict(size=6, opacity=0.8),
        name='Puts'
    ))
    fig_delta.add_vline(x=spot, line_dash="dash", line_color='#f85149', line_width=1.5)
    apply_dark_theme(fig_delta, 'Delta Profile')

    # 4. Open Interest
    fig_oi = go.Figure()
    # Call OI
    fig_oi.add_trace(go.Bar(
        x=df[df['right']=='C']['strike'] - 0.3,  # small offset
        y=df[df['right']=='C']['oi'],
        width=0.8,
        marker_color='#2ecc71',
        name='Call OI',
        opacity=0.95
    ))

    # Put OI
    fig_oi.add_trace(go.Bar(
        x=df[df['right']=='P']['strike'] + 0.3,
        y=df[df['right']=='P']['oi'],
        width=0.8,
        marker_color='#e74c3c',
        name='Put OI',
        opacity=0.95
    ))

    fig_oi.add_vline(x=spot, line_dash="dash", line_color='#f85149', line_width=1.5)
    apply_dark_theme(fig_oi, 'Open Interest')

    # 5. Trading Volume
    fig_vol = go.Figure()
    fig_vol.add_trace(go.Bar(
        x=df[df['right']=='C']['strike'] - 0.3,
        y=df[df['right']=='C']['volume'],
        width=0.8,
        marker_color='#2ecc71',
        name='Call Vol',
        opacity=0.95
    ))

    fig_vol.add_trace(go.Bar(
        x=df[df['right']=='P']['strike'] + 0.3,
        y=df[df['right']=='P']['volume'],
        width=0.8,
        marker_color='#e74c3c',
        name='Put Vol',
        opacity=0.95
    ))

    fig_vol.add_vline(x=spot, line_dash="dash", line_color='#f85149', line_width=1.5)
    apply_dark_theme(fig_vol, 'Trading Volume')

    # 6. Gamma Profile
    gamma_total = df.groupby('strike')['gamma'].sum().sort_index()  

    fig_gamma = go.Figure()
    fig_gamma.add_trace(go.Scatter(
        x=gamma_total.index,
        y=gamma_total.values,
        mode='lines',
        line=dict(color='#f0883e', width=3.5),  
        name='Gamma'
    ))
    fig_gamma.add_trace(go.Scatter(
        x=gamma_total.index,
        y=gamma_total.values,
        mode='lines',
        fill='tozeroy',
        fillcolor='rgba(240,136,62,0.35)',  
        line=dict(color='rgba(0,0,0,0)'),
        showlegend=False
    ))
    fig_gamma.add_vline(x=spot, line_dash="dash", line_color='#f85149', line_width=2)
    if not gamma_total.empty:
        max_g_strike = gamma_total.idxmax()
        max_g_value = gamma_total.max()
        fig_gamma.add_annotation(
            x=max_g_strike, y=max_g_value,
            text=f"MAX GAMMA: {max_g_strike}<br>{max_g_value:.4f}",
            showarrow=True,
            arrowhead=2,
            ax=40, ay=-50,
            font=dict(color='#ffa657', size=12),
            bgcolor='#161b22',
            bordercolor='#30363d'
        )
    apply_dark_theme(fig_gamma, 'Gamma Exposure Profile')
    fig_gamma.update_yaxes(range=[0, max(gamma_total.max() * 1.2, 0.05)]) #force y-axis to start at 0 and have some headroom

    header_text = (f"{analyzer.symbol}  •  Spot: ${spot:.2f}  •  Expiry: {expiry}  •  "
                   f"P/C Vol Ratio: {pc_ratio:.2f}  •  Updated: {datetime.now().strftime('%H:%M:%S')}")

    return fig_skew, fig_smile, fig_delta, fig_oi, fig_vol, fig_gamma, header_text


if __name__ == '__main__':
    app.run(debug=True)
    # If you want to run on a server or make it accessible on the local network, use the line below instead:
    # app.run(debug=True, host='0.0.0.0', port=8050)