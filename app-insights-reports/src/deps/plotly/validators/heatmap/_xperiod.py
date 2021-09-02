import _plotly_utils.basevalidators


class XperiodValidator(_plotly_utils.basevalidators.AnyValidator):
    def __init__(self, plotly_name="xperiod", parent_name="heatmap", **kwargs):
        super(XperiodValidator, self).__init__(
            plotly_name=plotly_name,
            parent_name=parent_name,
            edit_type=kwargs.pop("edit_type", "calc"),
            implied_edits=kwargs.pop("implied_edits", {"xtype": "scaled"}),
            **kwargs
        )
