from automation.app_agent import AppAgent


agent = AppAgent()


tests = [
    "Instagram",
    "Calculator",
    "Notepad",
]


for app_name in tests:

    print(
        "\nTrying:",
        app_name
    )

    try:

        result = agent.open_app(
            app_name
        )

        print(
            result
        )

    except Exception as error:

        print(
            "ERROR:",
            error
        )