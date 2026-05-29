{ pkgs, lib, config, inputs, ... }:

{
  # https://devenv.sh/languages/
  dotenv.enable = true;
  languages.python = {
    enable = true;
    uv = {
      enable = true;
      sync.enable = true;
    };
    venv.enable = true;
  };

  # https://devenv.sh/packages/
  packages = [ pkgs.git ];

  services.redis.enable = true;
}
