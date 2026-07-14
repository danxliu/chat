{ pkgs, lib, config, inputs, ... }:

{
  # https://devenv.sh/languages/
  dotenv.enable = true;
  languages.python = {
    enable = true;
    directory = "./backend";
    uv = {
      enable = true;
      sync.enable = true;
    };
    venv.enable = true;
  };

  languages.javascript = {
    enable = true;
    bun.enable = true;
  };

  # https://devenv.sh/packages/
  packages = [ pkgs.git ];

  services.redis = {
    enable = true;
    port = 6379;
  };

  processes.backend.exec = "cd backend && uv run main.py";
  processes.frontend.exec = "cd frontend && npm run dev";
}
