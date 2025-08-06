# 公司数据配置
COMPANY_DATA = [
    {
        "name": "American Express",
        "domain": "americanexpress.com",
        "website": "https://www.americanexpress.com"
    },
    {
        "name": "Amazon",
        "domain": "amazon.com",
        "website": "https://www.amazon.com"
    },
    {
        "name": "Bloomberg",
        "domain": "bloomberg.com",
        "website": "https://www.bloomberg.com"
    },
    {
        "name": "AXA",
        "domain": "axa.com",
        "website": "https://www.axa.com"
    },
    {
        "name": "Mercari",
        "domain": "mercari.com",
        "website": "https://www.mercari.com"
    },
    {
        "name": "NVIDIA",
        "domain": "nvidia.com",
        "website": "https://www.nvidia.com"
    },
    {
        "name": "Mapbox",
        "domain": "mapbox.com",
        "website": "https://www.mapbox.com"
    },
    {
        "name": "Nomura",
        "domain": "nomuraholdings.com",
        "website": "https://www.nomura.com"
    },
    {
        "name": "OKCoin",
        "domain": "okcoin.com",
        "website": "https://www.okcoin.com"
    },
    {
        "name": "Money Forward",
        "domain": "moneyforward.com",
        "website": "https://moneyforward.com"
    },
    {
        "name": "EPAM",
        "domain": "epam.com",
        "website": "https://www.epam.com"
    },
    {
        "name": "UBS",
        "domain": "ubs.com",
        "website": "https://www.ubs.com"
    },
    {
        "name": "Cybereason",
        "domain": "cybereason.com",
        "website": "https://www.cybereason.com"
    },
    {
        "name": "PayPay",
        "domain": "paypay.ne.jp",
        "website": "https://paypay.ne.jp"
    },
    {
        "name": "Morgan Stanley",
        "domain": "morganstanley.com",
        "website": "https://www.morganstanley.com"
    },
    {
        "name": "Google",
        "domain": "google.com",
        "website": "https://www.google.com"
    },
    {
        "name": "SmartNews",
        "domain": "smartnews.com",
        "website": "https://www.smartnews.com"
    },
    {
        "name": "Yahoo",
        "domain": "yahoo.com",
        "website": "https://www.yahoo.com"
    },
    {
        "name": "Woven",
        "domain": "woven-planet.global",
        "website": "https://www.woven-planet.global"
    },
    {
        "name": "Appier",
        "domain": "appier.com",
        "website": "https://www.appier.com"
    },
    {
        "name": "Japan AI",
        "domain": "japan-ai.co.jp",
        "website": "https://japan-ai.co.jp"
    },
    {
        "name": "Booking",
        "domain": "booking.com",
        "website": "https://www.booking.com"
    },
    {
        "name": "AnyMind",
        "domain": "anymindgroup.com",
        "website": "https://anymindgroup.com"
    },
    {
        "name": "ByteDance",
        "domain": "bytedance.com",
        "website": "https://www.bytedance.com"
    },
    {
        "name": "Shopee",
        "domain": "shopee.com",
        "website": "https://www.shopee.com"
    },
    {
        "name": "Decathlon",
        "domain": "decathlon.com",
        "website": "https://www.decathlon.com"
    }
]

def get_company_suggestions(query):
    """
    根据查询字符串返回匹配的公司建议
    """
    query = query.lower().strip()
    suggestions = []
    
    for company in COMPANY_DATA:
        if query in company["name"].lower():
            suggestions.append(company)
    
    # 按匹配度排序（完全匹配优先）
    suggestions.sort(key=lambda x: x["name"].lower().startswith(query), reverse=True)
    
    return suggestions[:10]  # 限制返回10个建议

def get_company_by_name(name):
    """
    根据公司名称获取公司信息
    """
    for company in COMPANY_DATA:
        if company["name"].lower() == name.lower():
            return company
    return None 