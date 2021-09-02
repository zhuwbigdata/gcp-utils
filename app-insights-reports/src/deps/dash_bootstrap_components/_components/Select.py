# AUTO GENERATED FILE - DO NOT EDIT

from dash.development.base_component import Component, _explicitize_args


class Select(Component):
    """A Select component.
Create a HTML select element with Bootstrap styles. Specify options as a
list of dictionaries with keys label, value and disabled.

Keyword arguments:

- id (string; optional):
    The ID of this component, used to identify dash components in
    callbacks. The ID needs to be unique across all of the components
    in an app.

- bs_size (string; optional):
    Set the size of the Input. Options: 'sm' (small), 'md' (medium) or
    'lg' (large). Default is 'md'.

- className (string; optional):
    Often used with CSS to style elements with common properties.

- disabled (boolean; optional):
    Set to True to disable the Select.

- invalid (boolean; optional):
    Apply invalid style to the Input for feedback purposes. This will
    cause any FormFeedback in the enclosing FormGroup with valid=False
    to display.

- key (string; optional):
    A unique identifier for the component, used to improve performance
    by React.js while rendering components See
    https://reactjs.org/docs/lists-and-keys.html for more info.

- name (string; optional):
    The name of the control, which is submitted with the form data.

- options (list; optional):
    An array of options for the select.

- persisted_props (list of a value equal to: 'value's; default ['value']):
    Properties whose user interactions will persist after refreshing
    the component or the page. Since only `value` is allowed this prop
    can normally be ignored.

- persistence (boolean | string | number; optional):
    Used to allow user interactions in this component to be persisted
    when the component - or the page - is refreshed. If `persisted` is
    truthy and hasn't changed from its previous value, a `value` that
    the user has changed while using the app will keep that change, as
    long as the new `value` also matches what was given originally.
    Used in conjunction with `persistence_type`.

- persistence_type (a value equal to: 'local', 'session', 'memory'; default 'local'):
    Where persisted user changes will be stored: memory: only kept in
    memory, reset on page refresh. local: window.localStorage, data is
    kept after the browser quit. session: window.sessionStorage, data
    is cleared once the browser quit.

- placeholder (string; default ''):
    Placeholder text to display before a selection is made.

- required (a value equal to: 'required', 'REQUIRED' | boolean; optional):
    This attribute specifies that the user must fill in a value before
    submitting a form. It cannot be used when the type attribute is
    hidden, image, or a button type (submit, reset, or button). The
    :optional and :required CSS pseudo-classes will be applied to the
    field as appropriate. required is an HTML boolean attribute - it
    is enabled by a boolean or 'required'. Alternative capitalizations
    `REQUIRED` are also acccepted.

- style (dict; optional):
    Defines CSS styles which will override styles previously set.

- valid (boolean; optional):
    Apply valid style to the Input for feedback purposes. This will
    cause any FormFeedback in the enclosing FormGroup with valid=True
    to display.

- value (string | number; default ''):
    The value of the currently selected option."""
    @_explicitize_args
    def __init__(self, id=Component.UNDEFINED, style=Component.UNDEFINED, className=Component.UNDEFINED, key=Component.UNDEFINED, placeholder=Component.UNDEFINED, value=Component.UNDEFINED, options=Component.UNDEFINED, disabled=Component.UNDEFINED, required=Component.UNDEFINED, valid=Component.UNDEFINED, invalid=Component.UNDEFINED, bs_size=Component.UNDEFINED, persistence=Component.UNDEFINED, persisted_props=Component.UNDEFINED, persistence_type=Component.UNDEFINED, name=Component.UNDEFINED, **kwargs):
        self._prop_names = ['id', 'bs_size', 'className', 'disabled', 'invalid', 'key', 'name', 'options', 'persisted_props', 'persistence', 'persistence_type', 'placeholder', 'required', 'style', 'valid', 'value']
        self._type = 'Select'
        self._namespace = 'dash_bootstrap_components'
        self._valid_wildcard_attributes =            []
        self.available_properties = ['id', 'bs_size', 'className', 'disabled', 'invalid', 'key', 'name', 'options', 'persisted_props', 'persistence', 'persistence_type', 'placeholder', 'required', 'style', 'valid', 'value']
        self.available_wildcard_properties =            []
        _explicit_args = kwargs.pop('_explicit_args')
        _locals = locals()
        _locals.update(kwargs)  # For wildcard attrs
        args = {k: _locals[k] for k in _explicit_args if k != 'children'}
        for k in []:
            if k not in args:
                raise TypeError(
                    'Required argument `' + k + '` was not specified.')
        super(Select, self).__init__(**args)
