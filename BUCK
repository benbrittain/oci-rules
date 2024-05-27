load("//oci:defs.bzl", "oci_pull", "oci_image")
load("//tar:defs.bzl", "tar_file")

http_archive(
  name="dive",
  urls=["https://github.com/wagoodman/dive/releases/download/v0.12.0/dive_0.12.0_linux_arm64.tar.gz"],
  sha256="a2a1470302cdfa367a48f80b67bbf11c0cd8039af9211e39515bd2bbbda58fea",
  #  strip_prefix='dive',
  sub_targets=["dive"],
)

tar_file(
  name = "dive-tar",
  srcs = [":dive[dive]"],
  out = "dive.tar",
)

oci_pull(
  name = "distroless",
  image = "gcr.io/distroless/base",
  digest = "sha256:ccaef5ee2f1850270d453fdf700a5392534f8d1a8ca2acda391fbb6a06b81c86",
  platforms = ["linux/arm64"],
)

oci_image(
  name = "image",
  base = ":distroless",
  tars = [":dive-tar"],
  entrypoint = ["/dive"],
)
