load(
    "@prelude//rules.bzl",
    "http_archive",
)
load(
    ":releases.bzl",
    crane_releases = "releases",
)

CraneReleaseInfo = provider(
    fields = {
        "version": provider_field(typing.Any, default = None),
        "url": provider_field(typing.Any, default = None),
        "sha256": provider_field(typing.Any, default = None),
    },
)

def _get_crane_release(version: str, platform: str) -> CraneReleaseInfo:
    if version not in crane_releases:
        fail("Unsupported crane version: {}".format(version))
    if platform not in crane_releases[version]:
        fail("Unsupported crane platform: {}".format(platform))

    return CraneReleaseInfo(
        version = version,
        url = crane_releases[version][platform]["url"],
        sha256 = crane_releases[version][platform]["sha256"],
    )

def _host_arch() -> str:
    arch = host_info().arch
    if arch.is_x86_64:
        return "x86_64"
    elif host_info().arch.is_aarch64:
        return "arm64"
    else:
        fail("Unsupported host architecture.")

def _host_os() -> str:
    os = host_info().os
    if os.is_linux:
        return "Linux"
    elif os.is_macos:
        return "Darwin"
    elif os.is_windows:
        return "Windows"
    else:
        fail("Unsupported host os.")

CraneInfo = provider(
    fields = {
        "version": provider_field(typing.Any, default = None),
        "arch": provider_field(typing.Any, default = None),
        "os": provider_field(typing.Any, default = None),
    },
)

def _crane_binary_impl(ctx: AnalysisContext) -> list[Provider]:
    dst = ctx.actions.declare_output("crane")
    src = ctx.attrs.bin[DefaultInfo].default_outputs[0]
    ctx.actions.run(["cp", cmd_args(src, format = "{}/crane"), dst.as_output()], category = "cp_crane")

    crane = cmd_args([dst], hidden = ctx.attrs.bin[DefaultInfo].default_outputs + ctx.attrs.bin[DefaultInfo].other_outputs)

    return [
        ctx.attrs.bin[DefaultInfo],
        RunInfo(args = crane),
        CraneInfo(
            version = ctx.attrs.version,
            arch = ctx.attrs.arch,
            os = ctx.attrs.os,
        ),
    ]

crane_binary = rule(
    impl = _crane_binary_impl,
    attrs = {
        "version": attrs.string(),
        "arch": attrs.string(),
        "os": attrs.string(),
        "bin": attrs.dep(providers = [DefaultInfo]),
    },
)

def download_crane_binary(
        name: str,
        version: str,
        arch: [None, str] = None,
        os: [None, str] = None):
    if arch == None:
        arch = _host_arch()
    if os == None:
        os = _host_os()

    archive_name = "go_containerregistry_{}_{}.tar.gz".format(os, arch)
    release = _get_crane_release(version, "{}-{}".format(os, arch))
    http_archive(
        name = archive_name,
        urls = [release.url],
        sha256 = release.sha256,
    )
    crane_binary(
        name = name,
        version = version,
        arch = arch,
        os = os,
        bin = ":{}".format(archive_name),
    )

OciToolchainInfo = provider(fields = {
    "crane": typing.Any,
})

def _oci_toolchain_impl(ctx) -> list[[DefaultInfo, OciToolchainInfo]]:
    return [
        DefaultInfo(),
        OciToolchainInfo(
            crane = ctx.attrs.crane,
        ),
    ]

oci_toolchain = rule(
    impl = _oci_toolchain_impl,
    attrs = {
        "crane": attrs.exec_dep(providers = [RunInfo]),
    },
    is_toolchain_rule = True,
)
