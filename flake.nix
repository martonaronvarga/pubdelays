{
  description = "Reproducible PubMed/MEDLINE publication-delay pipeline";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-parts.url = "github:hercules-ci/flake-parts";
  };

  outputs = inputs @ {flake-parts, ...}:
    flake-parts.lib.mkFlake {inherit inputs;} {
      systems = [
        "x86_64-linux"
        "aarch64-linux"
        "x86_64-darwin"
        "aarch64-darwin"
      ];

      perSystem = {
        self',
        pkgs,
        lib,
        ...
      }: let
        python = pkgs.python312;
        pythonPackages = python.pkgs;

        pubdelays = pythonPackages.buildPythonApplication {
          pname = "pubdelays";
          version = "0.1.0";
          src = ./.;
          pyproject = true;

          build-system = with pythonPackages; [
            setuptools
            wheel
          ];

          dependencies = with pythonPackages; [
            lxml
          ];

          nativeCheckInputs = with pythonPackages; [
            pytest
          ];

          checkPhase = ''
            runHook preCheck
            pytest -q
            runHook postCheck
          '';

          pythonImportsCheck = ["pubdelays"];
        };

        pythonEnv = python.withPackages (ps:
          with ps; [
            lxml
            pytest
          ]);

        rEnv = pkgs.rWrapper.override {
          packages = with pkgs.rPackages; [
            dplyr
            glue
            jsonlite
            fuzzyjoin
            tidyr
            readr
            lubridate
            stringr
            tibble
            purrr
          ];
        };
      in {
        packages.default = pubdelays;
        packages.pubdelays = pubdelays;

        apps.default = {
          type = "app";
          program = "${self'.packages.pubdelays}/bin/pubdelays-pipeline";
        };
        apps.pubdelays-pipeline = self'.apps.default;

        checks.default = pubdelays;

        devShells.default = pkgs.mkShell {
          packages = [
            pythonEnv
            rEnv
            pkgs.shellcheck
            pkgs.ruff
            pkgs.nixpkgs-fmt
          ];

          PYTHONPATH = "${toString ./.}/src";
          shellHook = ''
            exec zsh
          '';
        };

        formatter = pkgs.nixpkgs-fmt;
      };
    };
}
