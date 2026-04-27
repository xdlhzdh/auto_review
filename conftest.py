def pytest_addoption(parser):
    parser.addoption("--commit-functions", action="store", default="commit.functions", help="Path to the commit functions file")
    parser.addoption("--output", action="store", default="comment.html", help="Path to the gpt comment html")