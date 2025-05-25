import pandas as pd
from dash import Dash, dcc, html, Input, Output, State, dash_table
import plotly.graph_objects as go

# Load and prepare data
df = pd.read_csv("statement6231db41a228040279cdf4d768bb5cd0.csv")
df['Close Date'] = pd.to_datetime(df['Close Date'], errors='coerce')
df = df.dropna(subset=['Close Date', 'Symbol'])

currency_profit = df.groupby(['Symbol', 'Close Date'])['Profit'].sum().reset_index()
symbols = sorted(currency_profit['Symbol'].unique())

# Create Dash app
app = Dash(__name__)
app.title = "Forex Cumulative Profit Dashboard"

# Layout
app.layout = html.Div([
    html.H1("Cumulative Profit Dashboard", style={'textAlign': 'center'}),

    html.Div([
        html.Label("Select a Currency Pair:"),
        dcc.Dropdown(
            id='symbol-dropdown',
            options=[{'label': sym, 'value': sym} for sym in symbols],
            value=symbols[0],
            clearable=False
        )
    ], style={'width': '45%', 'display': 'inline-block', 'paddingRight': '20px'}),

    html.Div([
        html.Label("Select Date Range:"),
        dcc.DatePickerRange(
            id='date-picker',
            min_date_allowed=currency_profit['Close Date'].min().date(),
            max_date_allowed=currency_profit['Close Date'].max().date(),
            start_date=currency_profit['Close Date'].min().date(),
            end_date=currency_profit['Close Date'].max().date()
        )
    ], style={'width': '50%', 'display': 'inline-block'}),

    html.H3(id='profit-summary', style={'textAlign': 'center', 'marginTop': '30px'}),

    dcc.Graph(id='profit-graph'),

    html.Div([
        html.Button("Download Filtered Data", id="download-btn"),
        dcc.Download(id="download-data")
    ], style={'textAlign': 'center', 'margin': '20px'}),

    dash_table.DataTable(
        id='data-table',
        columns=[{"name": i, "id": i} for i in ['Close Date', 'Profit', 'Cumulative Profit']],
        style_table={'overflowX': 'auto'},
        style_cell={'textAlign': 'center'},
        page_size=10
    )
])

# Callback to update graph and table
@app.callback(
    [Output('profit-graph', 'figure'),
     Output('profit-summary', 'children'),
     Output('data-table', 'data')],
    [Input('symbol-dropdown', 'value'),
     Input('date-picker', 'start_date'),
     Input('date-picker', 'end_date')]
)
def update_dashboard(symbol, start_date, end_date):
    data = currency_profit[
        (currency_profit['Symbol'] == symbol) &
        (currency_profit['Close Date'] >= pd.to_datetime(start_date)) &
        (currency_profit['Close Date'] <= pd.to_datetime(end_date))
    ].sort_values('Close Date')

    if data.empty:
        return go.Figure(), "No data for selected range.", []

    data['Cumulative Profit'] = data['Profit'].cumsum()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=data['Close Date'],
        y=data['Cumulative Profit'],
        mode='lines',
        fill='tozeroy',
        name=symbol
    ))
    fig.update_layout(
        title=f"Cumulative Profit - {symbol}",
        xaxis_title="Close Date",
        yaxis_title="Cumulative Profit (USD)",
        hovermode='x unified',
        template='plotly_white'
    )

    total_profit = data['Cumulative Profit'].iloc[-1]
    summary_text = f"📈 Total Cumulative Profit for {symbol}: ${total_profit:,.2f}"

    # Prepare table
    data_table = data[['Close Date', 'Profit', 'Cumulative Profit']].copy()
    data_table['Close Date'] = data_table['Close Date'].astype(str)

    return fig, summary_text, data_table.to_dict('records')

# Callback to export data
@app.callback(
    Output("download-data", "data"),
    Input("download-btn", "n_clicks"),
    State("symbol-dropdown", "value"),
    State("date-picker", "start_date"),
    State("date-picker", "end_date"),
    prevent_initial_call=True
)
def download_filtered_data(n_clicks, symbol, start_date, end_date):
    filtered = currency_profit[
        (currency_profit['Symbol'] == symbol) &
        (currency_profit['Close Date'] >= pd.to_datetime(start_date)) &
        (currency_profit['Close Date'] <= pd.to_datetime(end_date))
    ].sort_values('Close Date')
    filtered['Cumulative Profit'] = filtered['Profit'].cumsum()
    return dcc.send_data_frame(filtered.to_csv, f"{symbol}_filtered_data.csv", index=False)

# Run the app
if __name__ == '__main__':
    app.run(debug=True)
