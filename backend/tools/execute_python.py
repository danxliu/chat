import docker


def execute_python(script: str) -> str:
    """Uses docker to execute a python script, returning the result. Includes a 30s timeout."""
    try:
        client = docker.from_env()
    except Exception as e:
        return f"Error initializing docker client: {e}"

    try:
        container = client.containers.run(
            "python:3.11-slim",
            command=["python", "-c", script],
            detach=True,
            mem_limit="128m",
            network_disabled=True,
        )

        try:
            result = container.wait(timeout=30)
            logs = container.logs().decode("utf-8")

            md_results = [f"### Execution Result (Exit Code {result['StatusCode']})"]
            md_results.append("```\n" + logs + "\n```")
            return "\n".join(md_results)
        except Exception as timeout_err:
            container.kill()
            return f"Execution timed out or failed: {timeout_err}"
        finally:
            container.remove(force=True)

    except Exception as e:
        return f"Error during docker execution: {e}"
