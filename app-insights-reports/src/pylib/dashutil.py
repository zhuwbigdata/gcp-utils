import dash


def invoker():
    ctx = dash.callback_context
    if not ctx.triggered:
        return None
    else:
        return ctx.triggered[0]['prop_id'].split('.')[0]


def component(children, id):
    if type(children)==dict:
        children = [children]
    if type(children)==list:
        for child in children:
            if child['props'].get('id')==id:
                return child
            child = component(child['props'].get('children', []), id)
            if child:
                return child
    return None


def prop(children, id, prop):
    comp = component(children, id)
    if comp:
        return comp['props'].get(prop)
    return None

