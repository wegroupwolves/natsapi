let
  pkgs = import <nixpkgs> {};
in pkgs.mkShell {
    shellHook = ''
        export PIP_NO_BINARY="ruff"
        set -a; source .env; set +a
        echo "SHELLHOOK LOG: .env loaded to ENV variables"
    '';

    packages = with pkgs; [
        python311

        ruff
        rustc
        cargo

        (poetry.override { python3 = python311; })

        (python311.withPackages (p: with p; [
            pip
            python-lsp-server
            pynvim
            pyls-isort
            python-lsp-black
        ]))

    ];

    env.LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath [
        pkgs.stdenv.cc.cc.lib
    ];
}
