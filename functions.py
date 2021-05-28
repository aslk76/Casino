from string import ascii_lowercase

def convert_si_to_number(i):
    if not i:
        return 0

    total_stars = 0
    alpha = ascii_lowercase.replace("k", "").replace("m", "").replace("b", "")

    i = i.strip().replace(",", ".").lower()

    if not i or any(char in alpha for char in i):
        return total_stars

    if len(i) >= 1:
        if 'k' in i:
            total_stars = float(i.replace('k', '')) * 1000
        elif 'm' in i:
            total_stars = float(i.replace('m', '')) * 1000000
        elif 'b' in i:
            total_stars = float(i.replace('b', '')) * 1000000000
        else:
            total_stars = int(i)

    return int(total_stars)


async def checkPers(id :int):
    async with bot.mplus_pool.acquire() as conn:
        async with conn.cursor() as cursor:
            query = """
                SELECT name , serv FROM persdict WHERE discord_id = %s
            """
            val = (id,)
            await cursor.execute(query,val)
            result = await cursor.fetchone()
            if result is not None:
                name = result[0]
                realm = result[1]
            else:
                name = None
                realm = None
    return (name, realm)