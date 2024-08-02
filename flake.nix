{
  inputs = {
    systems.url = "github:nix-systems/default";
  };

  outputs = {
    systems,
    nixpkgs,
    ...
  } @ inputs: let
    eachSystem = f:
      nixpkgs.lib.genAttrs (import systems) (
        system:
          f nixpkgs.legacyPackages.${system}
      );
  in {
    devShells = eachSystem (pkgs: {
      default = pkgs.mkShell {
        buildInputs = [
            pkgs.python311

            (pkgs.poetry.override { python3 = pkgs.python311; })

            (pkgs.python311.withPackages (p: with p; [
                pip
                python-lsp-server
                pynvim
                pyls-isort
                python-lsp-black
            ]))
        ];
      };
    });
  };
}
