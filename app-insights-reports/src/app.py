import dash
import dash_bootstrap_components as dbc

app = dash.Dash(
    __name__,
    assets_folder='jobs',
    assets_url_path='files',
    suppress_callback_exceptions=True,
    external_stylesheets=[dbc.themes.LUX],
)
