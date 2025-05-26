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
    html.Label("Select an EA:"),
    dcc.Dropdown(
        id='ea-file-dropdown',
        options=[
            {'label': 'EA 1', 'value': 'data/statement1e1ee36cf9536fa2f581c553705839b6.csv'},
            {'label': 'EA 2', 'value': 'data/statement6231db41a228040279cdf4d768bb5cd0.csv'},
            {'label': 'EA 3', 'value': 'data/statementecea4b2366f360ffedb3b7b8cbeb87d4.csv'},
        ],
        value='data/statement1e1ee36cf9536fa2f581c553705839b6.csv',
        clearable=False
    )
], style={'width': '40%', 'marginBottom': '20px'}),
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

    html.Br(),

    html.Div([
        html.Label("View Mode:"),
        dcc.RadioItems(
            id='view-mode',
            options=[
                {'label': 'Cumulative', 'value': 'cumulative'},
                {'label': 'Daily', 'value': 'daily'}
            ],
            value='cumulative',
            labelStyle={'display': 'inline-block', 'marginRight': '20px'}
        )
    ], style={'textAlign': 'center', 'marginTop': '20px'}),

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

# Callback to update graph, summary, and table@app.callback(
@app.callback(
    [Output('profit-graph', 'figure'),
     Output('profit-summary', 'children'),
     Output('data-table', 'data')],
    [Input('ea-file-dropdown', 'value'),
     Input('symbol-dropdown', 'value'),
     Input('date-picker', 'start_date'),
     Input('date-picker', 'end_date'),
     Input('view-mode', 'value')]
)
def update_dashboard(ea_file, symbol, start_date, end_date, view_mode):
    df = pd.read_csv(ea_file)
    df['Close Date'] = pd.to_datetime(df['Close Date'], errors='coerce')
    df = df.dropna(subset=['Close Date', 'Symbol'])

    currency_profit = df.groupby(['Symbol', 'Close Date'])['Profit'].sum().reset_index()

    data = currency_profit[
        (currency_profit['Symbol'] == symbol) &
        (currency_profit['Close Date'] >= pd.to_datetime(start_date)) &
        (currency_profit['Close Date'] <= pd.to_datetime(end_date))
    ].sort_values('Close Date')

    if data.empty:
        return go.Figure(), "No data for selected range.", []

    if view_mode == 'cumulative':
        data['Cumulative Profit'] = data['Profit'].cumsum()
        y_data = data['Cumulative Profit']
        y_title = "Cumulative Profit (USD)"
        summary_text = f"📈 Total Cumulative Profit: ${y_data.iloc[-1]:,.2f}"
    else:
        y_data = data['Profit']
        y_title = "Daily Profit (USD)"
        data['Cumulative Profit'] = data['Profit'].cumsum()
        summary_text = f"📅 Total Daily Profit: ${y_data.sum():,.2f}"

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=data['Close Date'],
        y=y_data,
        mode='lines+markers',
        fill='tozeroy' if view_mode == 'cumulative' else None,
        name=symbol
    ))
    fig.update_layout(
        title=f"{view_mode.capitalize()} Profit - {symbol}",
        xaxis_title="Close Date",
        yaxis_title=y_title,
        hovermode='x unified',
        template='plotly_white'
    )

    table_data = data[['Close Date', 'Profit', 'Cumulative Profit']].copy()
    table_data['Close Date'] = table_data['Close Date'].astype(str)

    return fig, summary_text, table_data.to_dict('records')

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

# Run app
if __name__ == '__main__':
    app.run(debug=True)
