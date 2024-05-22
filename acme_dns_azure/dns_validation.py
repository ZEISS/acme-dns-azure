from acme_dns_azure.log import setup_custom_logger
import dns.resolver

logger = setup_custom_logger(__name__)


class DNSChallenge:
    def __init__(self) -> None:
        pass

    def _zone_for_name(self, name: str) -> str | None:
        """
        Resolves the DNS zone and returns it as string.
        Needs associated child DNS absolute name (FQDN).
        """
        try:
            resolver = dns.resolver.Resolver()
            resolver.timeout = 2.0
            resolver.lifetime = 5.0
            zone = dns.resolver.zone_for_name(name, resolver=resolver).to_text(True)
            msg = "{0}._zone_for_name - Answer: {1}"
            logger.debug(msg.format(self.__class__.__name__, zone))
            return zone
        except dns.exception.DNSException as ex:
            msg = "{0}._zone_for_name - An DNS exception of type {1} occurred. {2}"
            logger.debug(msg.format(self.__class__.__name__, type(ex).__name__, ex))
        return None

    def _nameservers(self, zone: str) -> list[str]:
        """
        Resolves nameservers and returns their IPs as a list of strings.
        Returns None when no nameservers were found. Need associated DNS zone.
        """
        nameservers = []
        ns_r = self._resolve(zone, "NS")
        if ns_r:
            for ns in ns_r:
                for ip_rdtype in ["A", "AAAA"]:
                    ip_r = self._resolve(ns.to_text(), ip_rdtype)
                    if ip_r:
                        for ip in ip_r:
                            if ip.to_text() not in nameservers:
                                nameservers.append(ip.to_text())
        if not nameservers:
            msg = "{0}._nameservers - Nameservers for DNS zone not found: {1}"
            logger.debug(msg.format(self.__class__.__name__, zone))
        elif self._resolve(zone, "NS", nameservers) is None:
            msg = "{0}._nameservers - Nameservers for DNS zone not reachable: {1}"
            logger.debug(msg.format(self.__class__.__name__, zone))
            nameservers = []
        return nameservers

    def _resolve(
        self, name: str, rdtype: str, nameservers: list[str] = []
    ) -> dns.resolver.Answer | None:
        """
        Resolves DNS using specified or system default nameservers. It returns the DNS
        answer The answer is None when an DNS exception occurred.
        """
        try:
            resolver = dns.resolver.Resolver()
            resolver.timeout = 2.0
            resolver.lifetime = 5.0
            if nameservers:
                resolver.nameservers = nameservers
            r = resolver.resolve(name, rdtype)
            msg = "{0}._resolve - Answer: {1}".format(
                self.__class__.__name__, r.rrset.to_text().replace("\n", " | ")
            )
            logger.debug(msg)
            return r
        except dns.exception.DNSException as ex:
            msg = "{0}._resolve - An DNS exception of type {1} occurred. {2}"
            logger.debug(msg.format(self.__class__.__name__, type(ex).__name__, ex))
        return None

    def validate(self, name: str) -> tuple[str | None, str | None]:
        """
        First, determines the canonical name of given name by using the associated DNS zone and
        nameservers. Second, checks if the associated DNS challenge text record name exists.
        It returns the DNS Zone and the existing DNS challenge text record name as tuple.
        """
        name = "_acme-challenge." + name.removeprefix("*.")
        zone = None
        nameservers = []
        cname = None
        record = None
        hop, max_hops = 0, 2
        while True:
            qname = cname if cname else name
            qzone = self._zone_for_name(qname)
            if zone != qzone:
                zone = qzone
                nameservers = self._nameservers(zone)
            cname_r = self._resolve(qname, "CNAME", nameservers)
            if cname_r is None:
                break
            cname = dns.name.from_text(cname_r[0].to_text()).to_text(True)
            hop += 1
            if hop >= max_hops:
                msg = (
                    "{0}.validate - DNS record set {1} has a canonical name that points {2!s} "
                    "or more times to another canonical name. Avoid canonical name loops!"
                )
                logger.error(msg.format(self.__class__.__name__, name, hop))
                raise AssertionError
        qname_rel = (
            dns.name.from_text(qname).relativize(dns.name.from_text(zone)).to_text(True)
        )
        txt_r = self._resolve(qname, "TXT", nameservers)
        if txt_r:
            for value in txt_r:
                if value.to_text().strip("'\"") == "-":
                    record = qname_rel
                    break
        if cname and record is None and name != qname_rel:
            msg = (
                "{0}.validate - The DNS record set {1} has a canonical name, but its relative "
                "name does not correspond to the original record, nor does there exist an "
                "text record {2} that contains the value '-'. "
                "Create/modify respective record set upfront!"
            )
            logger.error(msg.format(self.__class__.__name__, name, qname))
            raise AssertionError
        msg = "{0}.validate - QName: {1} | CName: {2} | Zone: {3} | Record: {4}"
        logger.info(msg.format(self.__class__.__name__, name, cname, zone, record))
        return zone, record
