from backend.evaluation.parameter_optimizer import StrategyParameterOptimizer


def test_optimizer_insufficient_data():
    optimizer = StrategyParameterOptimizer()
    optimizer._build_samples = lambda **kwargs: []  # type: ignore[method-assign]
    result = optimizer.run(trials=5, min_samples=20)
    assert result["status"] == "insufficient_data"
    assert result["sample_count"] == 0


def test_optimizer_run_returns_best_trial():
    optimizer = StrategyParameterOptimizer()
    optimizer._build_samples = lambda **kwargs: [  # type: ignore[method-assign]
        {
            "recommendation_date": "2024-01-15",
            "stock_code": "000001",
            "return_5d": 1.2,
            "excess_return_5d": 0.4,
            "raw_scores": {"ma": 20, "rsi": 8, "volume": 6, "momentum": 4},
        },
        {
            "recommendation_date": "2024-01-15",
            "stock_code": "000002",
            "return_5d": -0.5,
            "excess_return_5d": -0.3,
            "raw_scores": {"ma": -12, "rsi": -5, "volume": -3, "momentum": -2},
        },
        {
            "recommendation_date": "2024-01-16",
            "stock_code": "000003",
            "return_5d": 2.0,
            "excess_return_5d": 1.0,
            "raw_scores": {"ma": 15, "rsi": 10, "volume": 5, "momentum": 9},
        },
    ]
    result = optimizer.run(trials=6, min_samples=2)
    assert result["status"] == "ok"
    assert result["sample_count"] == 3
    assert "best" in result
    assert "top_trials" in result
    assert len(result["top_trials"]) >= 1
