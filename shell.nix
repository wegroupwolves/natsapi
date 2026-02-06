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
    ];

    env.LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath [
        pkgs.stdenv.cc.cc.lib
    ];
}
