import requests
import datetime
import re

from helper.vigor2130_helpers import encode, LoginException, UnknownStatusException, NotLoggedInException


class Vigor2130:
    """The Vigor2130 object contains all functions to interact with the Vigor 2130 fiber modem

    Attributes:
        url (str): Base url to connect to the modem. E.g. http://192.168.1.254
        username (str): The encoded username
        password (str): The encoded password
        proxies (dict): Dictionary that holds the proxies to use, if any
        cookies (dict): Dictionary with necessary cookies to login to and interact with the modem

    """

    dhcp_leases_path = '/cgi-bin/webstax/stat/grocx_dhcp_status'
    arp_cache_path = '/cgi-bin/webstax/config/arp_table'
    sessions_path = '/cgi-bin/webstax/stat/session'
    dataflow_path = '/cgi-bin/webstax/config/dig_datam'
    ip_mac_bind_path = '/cgi-bin/webstax/config/ipbmac'
    system_log_path = '/cgi-bin/webstax/stat/syslog'
    traffic_control_path = '/cgi-bin/webstax/config/acl_traffic_edit'

    def __init__(self, url, username, password, proxies=None):
        """Init function for the Vigor2130 class

        Args:
            url (str): Base url to connect to the modem. E.g. http://192.168.1.254
            username (str): The username
            password (str): The password
            proxies (dict): A dictionary with proxies to use. Pass an empty dictionary {} or None for no proxies

        """
        self.url = url
        self.username = encode(username)
        self.password = encode(password)
        self.proxies = proxies if proxies is not None else {}
        self.cookies = {}
        self.logged_in = False

    def logout(self):
        try:
            requests.get(
                f'{self.url}/cgi-bin/webstax/login/logout',
                cookies=self.cookies,
                allow_redirects=False,
                proxies=self.proxies
            )
        except Exception as ex:
            print(ex)

        self.logged_in = False

    def login(self):
        """Login function for the Vigor2130 modem

        Raises:
            LoginException: Raised if the login attempt was not successful

        """
        r = requests.post(
            f'{self.url}/cgi-bin/webstax/login/login',
            data={'aa': self.username, 'ab': self.password},
            allow_redirects=False,
            proxies=self.proxies
        )
        if r.headers['location'].startswith('/index.htm'):
            self.cookies = {cookie.name: cookie.value for cookie in r.cookies if cookie.name == 'SESSION_ID_VIGOR'}
            self.logged_in = True
        else:
            self.logged_in = False
            raise LoginException()

    def post(self, url, data):

        if not self.logged_in:
            self.login()

        return requests.post(
            f'{self.url}{url}',
            data=data,
            cookies=self.cookies,
            allow_redirects=False,
            proxies=self.proxies
        )

    def get(self, url, encoding='utf-8'):
        """Reusable get function to execute a requests get call and interpret the response

        Args:
            url (str): Relative url to get
            encoding (str): The encoding to use when interpreting the response body

        Returns:
            str: The content returned by the get request

        Raises:
            LoginException: Raised if the login attempt was not successful
            NotLoggedInException: Raised if the call was successful but the request got redirected to the login page
            UnknownStatusException: Raised if the call was not successful due to an unknown condition

        """

        if not self.logged_in:
            self.login()

        r = requests.get(
            f'{self.url}{url}',
            cookies=self.cookies,
            allow_redirects=False,
            proxies=self.proxies
        )

        if r.status_code == 200:
            return r.content.decode(encoding)

        if r.status_code == 302 and r.headers['location'].startswith('/login.htm'):
            self.logged_in = False
            raise NotLoggedInException()

        raise UnknownStatusException()

    def get_dhcp_leases(self):

        content = self.get(self.dhcp_leases_path)

        return [{'computer_name': z[0].lower(), 'ip_address': z[1], 'mac_address': z[2].lower(),
                 'expire_minutes': int(z[3])} for z in
                [y.split('/') for y in
                 [x for x in content.split('|') if x != '']]]

    def get_arp_cache(self):

        content = self.get(self.arp_cache_path)

        return [{'ip_address': z[0], 'mac_address': z[1].lower()} for z in
                [y.split('\t') for y in
                 [x for x in content.split('\n') if not x.startswith('IP Address')]]]

    def get_sessions(self):

        content = self.get(self.sessions_path)

        return [{
            'protocol': z[0].lower(),
            'src_ip': z[1].split(':')[0],
            'src_port': int(z[1].split(':')[1]),
            'dst_ip': z[2].split(':')[0],
            'dst_port': int(z[2].split(':')[1]),
            'state': z[3].lower() if len(z) == 4 else ''
        } for z in
            [y.split(' ') for y in
             [x for x in content.split('\n')]] if len(z) >= 3]

    def get_global_dataflow(self):

        return [{
            'ip_address': z[0],
            'nr_sessions': int(z[1]),
            'hardware_nat_rate_kbs': int(z[2])
        } for z in
            [y.split(',') for y in
             [x for x in self.get(self.dataflow_path).split('|')[2].split(';') if x.strip() != '']]
        ]

    def get_detailed_dataflow(self):

        return [{
            'ip_address': z[0],
            'tx_rate_kbs': int(z[1]),
            'rx_rate_kbs': int(z[2])
        } for z in
            [y.split(',') for y in
             [x for x in self.get(self.dataflow_path).split('|')[3].split(';') if x.strip() != '']]
        ]

    def get_mac_ip_bind(self):

        return [{
            'ip_address': y[0],
            'mac_address': y[1].lower(),
            'computer_name': y[2].lower()
        } for y in
            [x.split(',') for x in
             self.get(self.ip_mac_bind_path).split('/')[2].split('|') if x.strip() != ''] if y[2].strip() != ''
        ]

    def get_system_log(self):
        now = datetime.datetime.now()
        current_month = now.month
        current_year = now.year

        for line in self.get(self.system_log_path).split('\n'):
            if len(line.strip()) > 0:
                parts = re.sub(
                    r'^([a-zA-Z0-9 :]{15}) ([^ ]+) ([a-zA-Z0-9]+)\.([a-zA-Z]+) ([^:]*):(.*)$',
                    r'\1\t\3\t\4\t\5\t\6',
                    line
                ).split('\t')
                try:
                    year = current_year - 1 if 'Dec' in parts[0] and current_month == 1 else current_year
                    yield {
                        'timestamp': int(datetime.datetime.strptime(
                            f'{year} {parts[0].strip()}',
                            '%Y %B %d %H:%M:%S'
                        ).timestamp()),
                        'source': parts[1].strip(),
                        'level': parts[2].strip(),
                        'daemon': parts[3].strip(),
                        'message': parts[4].strip()
                    }
                except IndexError as e:
                    raise Exception(f'Could not parse line {line}')

    def block_ip(self, ip: str):
        return self.post(
            url=self.traffic_control_path,
            data={
                'iRuleEn': '1', 'sRuleNm': f'block-{ip.replace(".", "-")}',
                'sSrc': 'wan', 'sDes': 'lan',
                'sPro': 'tcpudp', 'sp_start': '',
                'sp_end': '', 'dp_start': '',
                'dp_end': '', 'sSrcIp': ip,
                'sDesIp': '', 'txtMac1': '',
                'txtMac2': '', 'txtMac3': '',
                'txtMac4': '', 'txtMac5': '',
                'txtMac6': '', 'sTarget': 'DROP',
                'sTimeProf': '-1', 'idx': '-1',
                'sp': '', 'dp': '',
                'sSrcMac': ''
            }
        ).status_code
