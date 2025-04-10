{pkgs}: {
  deps = [
    pkgs.libsodium
    pkgs.sqlite
    pkgs.postgresql
    pkgs.openssl
  ];
}
