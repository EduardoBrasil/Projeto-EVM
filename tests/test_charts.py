from charts import ChartBuilderFactory


def sample_history():
    return [
        {"sprint_no": 1, "PV": 100, "EV": 80, "AC": 90, "CPI": 0.89, "SPI": 0.8},
        {"sprint_no": 2, "PV": 120, "EV": 100, "AC": 110, "CPI": 0.91, "SPI": 0.83},
    ]


def test_chart_factory_builds_all_supported_charts():
    factory = ChartBuilderFactory()

    for chart_type in ("cumulative", "cpi", "spi"):
        figure = factory.create(chart_type).build(sample_history())
        assert figure is not None


def test_chart_builder_handles_empty_history():
    factory = ChartBuilderFactory()
    figure = factory.create("cumulative").build([])
    assert figure is not None


def test_cumulative_chart_uses_cumulative_series():
    factory = ChartBuilderFactory()
    figure = factory.create("cumulative").build(sample_history())
    axes = figure.axes[0]
    lines = axes.get_lines()

    ac_series = list(lines[0].get_ydata())
    ev_series = list(lines[1].get_ydata())
    pv_series = list(lines[2].get_ydata())

    assert ac_series == [90, 200]
    assert ev_series == [80, 180]
    assert pv_series == [100, 220]
