import argparse
import logging
import os
import six
import subprocess


LETSENCRYPT_SAN_LIMIT = 100

logger = logging.getLogger(__name__)


class ACMEException(BaseException):
    pass


class DomainsMissing(ACMEException):
    pass


class MisconfiguredCommands(ACMEException):
    pass


def _generate_certificate(domains, **options):
    subprocess_args = [
        'sudo',
    ]

    # split the python location (if any) from the certbot path
    subprocess_args += [six.moves.shlex_quote(part) for part in options.get('certbot_command', '').split()]

    subprocess_args += [
        'certonly',
        '--noninteractive',
        '--preferred-challenges=http-01',
        '--manual',
        '--manual-public-ip-logging-ok',
        '--manual-auth-hook={0}'.format(six.moves.shlex_quote(options.get('auth_script', ''))),
        '--domains={0}'.format(six.moves.shlex_quote(domains))
    ]

    account = options.get('account', None)
    if account is not None:
        subprocess_args.append('--account={0}'.format(account))

    rsa_key_size = options.get('rsa_key_size', None)
    if rsa_key_size:
        subprocess_args.append('--rsa-key-size={0}'.format(six.moves.shlex_quote(str(rsa_key_size))))

    if options.get('allow_domain_subset', False):
        subprocess_args.append('--allow-subset-of-names')

    # default to maintaining certbot(-auto) version to minimize breakage
    if not options.get('allow_self_upgrade', False):
        subprocess_args.append('--no-self-upgrade')

    if not options.get('production', False):
        subprocess_args.append('--staging')

    if options.get('redirect', False):
        subprocess_args.append('--redirect')

    if options.get('hsts', False):
        subprocess_args.append('--hsts')

    if options.get('must_staple', False):
        subprocess_args.append('--must-staple')

    if options.get('staple_ocsp', False):
        subprocess_args.append('--staple-ocsp')

    if options.get('uir', False):
        subprocess_args.append('--uir')

    logger.debug('certbot subprocess arguments: %s', subprocess_args)

    proc = subprocess.Popen(subprocess_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = proc.communicate()

    logger.debug('certbot subprocess result code: %s', proc.returncode)
    if proc.returncode:
        logger.debug('certbot subprocess stdout:\n%s', out)
        logger.debug('certbot subprocess stderr:\n%s', err)

    return {
        'success': not bool(proc.returncode),
        'stdout': out,
        'stderr': err
    }


# NOTE: keyword-based arguments instead of parameters to allow for future adjustment
# related to `certbot` changes - less likely to break users code
def generate_certificate(**options):
    # Possible parameters, all map approximately to certbot options:
    # [
    # 'account', 'allow_domain_subset', 'allow_self_upgrade',
    # 'auth_script', 'certbot_command', 'domains', 'hsts',
    # 'must_staple', 'production', 'redirect', 'rsa_key_size',
    # 'san_ucc', 'staple_ocsp', 'uir'
    # ]
    # Generate this list using --generate_function_params

    domains = options.pop('domains', [])
    if not domains:
        raise DomainsMissing

    if isinstance(domains, six.string_types):
        domains = [domains]

    if not options.get('certbot_command') or not options.get('auth_script'):
        raise MisconfiguredCommands

    if options.get('san_ucc', False):
        # TODO: split domains into chunks of 100 (or 99?)
        # NOTE: the first item in each chunk of 100 will be
        # set as the CN for the cert
        logger.debug('Generating SAN certificate for %s', domains)
        _result = _generate_certificate(','.join(domains), **options)
        results = dict([(d, _result) for d in domains])
    else:
        results = {}
        for domain in domains:
            logger.debug('Generating one certificate for %s', domain)
            results[domain] = _generate_certificate(domain, **options)

    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", action="store_true", default=False, help="Verbose output")
    parser.add_argument("--generate_function_params", action="store_true", default=False,
                        help="Display all `generate_certificate` parameters (for developers integrating this library)")
    parser.add_argument('-d', '--domains', type=str, default=None,
                        help="Comma-separated list of domains for which to create a certificate(s)")
    parser.add_argument('-a', '--auth-script', default=None,
                        help="Full path to auth hook script; no spaces allowed")
    parser.add_argument('-c', '--certbot-command', default=None,
                        help="Full path to `certbot`/`certbot-auto`")
    parser.add_argument('--account', default=None,
                        help="Account ID to use for registering domains")
    parser.add_argument('--rsa-key-size', type=int, default=None,
                        help="RSA key size to use for certificate generation")
    parser.add_argument('-s', '--san-ucc', action='store_true', default=False,
                        help="If multiple domains are specified, this indicates whether to bundle up to "
                             "{0} domains into a single SAN/UCC certificate (default is false)".format(
                            LETSENCRYPT_SAN_LIMIT))
    parser.add_argument("--allow-domain-subset", action="store_true", default=False,
                        help="Allow certificate generation to succeed even if a subset of domains fail to authorize (default is false)")
    parser.add_argument('--must-staple', action='store_true', default=False,
                        help="Adds the OCSP Must Staple extension to the certificate (default is false)")
    parser.add_argument('--staple-ocsp', action='store_true', default=False,
                        help="Enables OCSP Stapling (default is false)")
    parser.add_argument('--hsts', action='store_true', default=False,
                        help="Add the Strict-Transport-Security header to every HTTP response (default is false)")
    parser.add_argument('--uir', action='store_true', default=False,
                        help="Add the \"Content-Security-Policy: upgrade-insecure-requests\" header to every HTTP response (default is false)")
    parser.add_argument('--redirect', action='store_true', default=False,
                        help="Automatically redirect all HTTP traffic to HTTPS for the newly authenticated vhost (default is false)")
    parser.add_argument('--allow-self-upgrade', action='store_true', default=False,
                        help="Permit automatic certbot upgrades (only applies when using certbot-auto; default is false)")
    parser.add_argument('--production', action='store_true', default=False,
                        help="Use production Let's Encrypt servers. (default is false)")

    args = parser.parse_args()

    if args.verbose:
        logger_level = logging.DEBUG
    else:
        logger_level = logging.INFO

    logging.basicConfig(format='%(asctime)-15s %(levelname)-8s %(name)-5s %(message)s')
    logger.setLevel(logger_level)

    options = vars(args)
    if args.generate_function_params:
        parser.exit(status=0, message="keyword arguments only (order unimportant):\ngenerate_certificate({0})\n".format(", ".join(sorted([p for p in options.keys() if p not in ['verbose', 'generate_function_params']]))))

    if not args.domains:
        parser.error('argument -d/--domains is required')
    if not args.certbot_command:
        parser.error('argument -c/--certbot-command is required')
    if not args.auth_script:
        parser.error('argument -c/--auth-script is required')

    # do some quick overrides of arguments
    options['domains'] = args.domains.split(',') if args.domains else []
    options['certbot_command'] = args.certbot_command or os.getenv('LETSENCRYPT_CERTBOT_COMMAND', '')
    options['auth_script'] = args.auth_script or os.getenv('LETSENCRYPT_AUTH_HOOK_SCRIPT', '')
    options['account'] = args.account or os.getenv('LETSENCRYPT_ACCOUNT', None)

    results = generate_certificate(**options)

    for domain, result in six.iteritems(results):
        if result.get('success', False):
            logger.info('SSL certificate successfully generated for %s', domain)
        else:
            logger.info('Could not generate SSL certificate for %s', domain)

if __name__ == "__main__":
    main()

# LETSENCRYPT_CERTBOT_COMMAND="/vagrant/certbot/venv/local/bin/python /vagrant/certbot/venv/local/bin/certbot" LETSENCRYPT_AUTH_HOOK_SCRIPT="/vagrant/certbot/test-auth-hook.sh"