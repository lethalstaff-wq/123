# Аудит: продукт, твики и обещания

Независимая проверка утверждений исследователей по первоисточникам.

# АУДИТ 12 ИССЛЕДОВАТЕЛЕЙ + ИТОГОВАЯ СТРАТЕГИЯ

**Метод:** WebSearch-бюджет сессии был исчерпан (200/200) до моего первого вызова — та же проблема, что у исследователей 2 и 4. Верификация сделана ~20 прямыми WebFetch/curl-запросами к первоисточникам с браузерным UA. Дата съёма: 2026-09-12.

---

## 1. ВЕРИФИКАЦИЯ 20 САМЫХ НАГРУЖЕННЫХ УТВЕРЖДЕНИЙ

| # | Утверждение | Вердикт | Проверка |
|---|---|---|---|
| 1 | EXM = lifetime, НЕ подписка; $29.99/$49.99 | **ПОДТВЕРЖДЕНО ТОЧНО** | Спарсил `window.pricingData`: `purchase_type` встречается 11 раз, **все 11 = `"lifetime"`**. `price_cents`: 2999/5499/7499/9999 (Plus), 4999/8999/12999/16999 (Premium). Нуль recurring-полей |
| 2 | Refund Policy: "one-time purchases, not subscriptions" | **ПОДТВЕРЖДЕНО ДОСЛОВНО** | «EXM Plus and EXM Premium are one-time purchases, not subscriptions. There is no recurring charge, no billing period, and nothing to cancel» |
| 3 | Юрлицо Slovakia s.r.o. + Stripe | **ПОДТВЕРЖДЕНО ДОСЛОВНО** | «made from EXM TWEAKS s.r.o., registered in Slovakia… Payments are processed by Stripe» |
| 4 | EXM возвращает деньги за покупку несовершеннолетним | **ПОДТВЕРЖДЕНО ДОСЛОВНО** | «A minor purchased without permission. A purchase made by someone under 18 without the consent of a parent or guardian» |
| 5 | Velocity Tweaks $5.99/мес, $3.99/мес годовой, $70 lifetime | **ПОДТВЕРЖДЕНО ТОЧНО** | velocitytweaks.com/premium, все три тира дословно |
| 6 | Paddle запрещает PC-оптимизаторы | **ПОДТВЕРЖДЕНО ДОСЛОВНО — Paddle ИСКЛЮЧЁН** | AUP: «Technical support services, including any software or service, marketed to repair, maintain, or improve the performance or security of an Electronic Device» + «System Health Products… Device Cleaners» |
| 7 | Stripe не работает ни в одной стране СНГ | **ПОДТВЕРЖДЕНО** | stripe.com/global: grep по KZ/GE/AM/UA/RU/BY/UZ/AZ/MD/KG = **0 совпадений на все 10** |
| 8 | Lemon Squeezy платит на банк в AM/AZ/KZ/MD/UZ, но не GE/UA/BY/KG | **ПОДТВЕРЖДЕНО** | Kazakhstan в payout-списке; Georgia/Ukraine/Belarus/Kyrgyzstan = 0 совпадений |
| 9 | Россия заблокирована у LS как ПОКУПАТЕЛЬ | **ПОДТВЕРЖДЕНО ДОСЛОВНО** | «We cannot accept payments from customers in the following countries: … Russian Federation …» (список из 18 стран совпал полностью) |
| 10 | Visa VAMP: 0.5% ratio ПРИ 5 диспутах | **ПОДТВЕРЖДЕНО ТОЧНО** | Stripe docs: VAMP count non-compliant **5**, ratio **0.5%**; excessive 150 CEMEA/1500 иначе, 2.2%/1.5% |
| 11 | Mastercard ECM 100-299 диспутов и 1.5-2.99% | **ПОДТВЕРЖДЕНО, но шкала штрафов в summary ИСПРАВЛЕНА** | См. коррекцию A ниже |
| 12 | MS Artifact Signing: физлицам только US/Canada | **ПОДТВЕРЖДЕНО ДОСЛОВНО** | «Individual developers must be located in the United States or Canada». Организации: US, CA, EU, UK, AU, NZ, JP, KR, SG, CH, NO, IL. Валидация 1-20 рабочих дней |
| 13 | DLSS 5 роняет FPS на 51% (NBA 2K27, RTX 5090) | **ПОДТВЕРЖДЕНО + НОВЫЕ ДАННЫЕ** | XDA/Digital Foundry: 128.4 → 62.7 FPS = −51.2%. **Дополнительно: RTX 5080 −58.4% (42.6 FPS)** |
| 14 | EA Javelin имеет публичный denylist драйверов | **ПОДТВЕРЖДЕНО ПОФАЙЛОВО** | Извлёк из help.ea.com: `winring0x64.sys`, `cpuz141_x64.sys`, `hwinfo64a.sys`, `ntiolib_x64.sys`, `winio64.sys`, `magdrvamd64.sys`, `dbutil_2_3.sys`, Core Temp, Process Explorer, Razer Synapse, reWASD, Daemon Tools, Voicemod, **IObit** |
| 15 | BattlEye блокирует софт с уязвимыми kernel-драйверами | **ПОДТВЕРЖДЕНО ДОСЛОВНО** | «BattlEye is blocking certain software that is using kernel drivers which contain known security issues that can be exploited by cheats. We cannot support such software and therefore cannot provide a fix» |
| 16 | BattlEye требует выключить NVIDIA Low Latency Mode | **ПОДТВЕРЖДЕНО ДОСЛОВНО** | «it is caused by NVIDIA's new "(Ultra-)Low Latency Mode"… please disable this feature» |
| 17 | MS категория "Tampering software" покрывает твикеры | **ПОДТВЕРЖДЕНО ДОСЛОВНО** | Включает: «Disabling or uninstalling security software», «Manipulating system components: … kernel drivers or system services», «**Unauthorized registry changes**: Modifications to the Windows Registry or system settings that impact the security posture», «Tampering with boot processes», «Disrupting critical services» |
| 18 | Маркетинг «+50 FPS» сам по себе — критерий unwanted software | **ПОДТВЕРЖДЕНО ДОСЛОВНО** | «Display exaggerated claims about your device's health»; «Display claims in an alarming manner about your device's health and **require payment** or certain actions in exchange for fixing the purported problems» |
| 19 | Блок-лист драйверов включён по умолчанию с Win11 2022 Update | **ПОДТВЕРЖДЕНО ДОСЛОВНО** | «Since the Windows 11 2022 update, the vulnerable driver blocklist is enabled by default for all devices»… «HVCI is on by-default for most new Windows 11 devices»… «updated quarterly» |
| 20 | Discord-монетизация недоступна оператору из СНГ | **ПОДТВЕРЖДЕНО ДОСЛОВНО** | «Premium Apps is not currently available outside of these regions» (US/EU/UK), «Team owner must be at least 18 years old», «App must be verified» |

**Бонус-верификация (RevenueCat 2026):** медианы $5.99 нед / $10.00 мес / $34.80 год; NA $6.99/$9.99/$39.99; IN-SEA $4.61/$3.75/$18.32; Gaming 82% weekly, lifetime в 18% пейволлов, **Y1 revenue per payer $11.22** — всё подтверждено.

---

## 2. ИСПРАВЛЕНИЯ, ПРОТИВОРЕЧИЯ, ПЛОХИЕ ДАННЫЕ

### A. ФАКТИЧЕСКИЕ ОШИБКИ (исправлены по первоисточнику)

**A1. Шкала штрафов Mastercard ECM — в summary `payments_stack` неверно.** Написано «escalate to $25,000-$50,000 by months 4-5». Реально (Stripe docs):
```
ECM:  мес 1=$0 | 2-3=$1,000 | 4-6=$5,000 | 7-11=$25,000 | 12-18=$50,000 | 19+=$100,000
HECM: мес 1=$0 | 2=$1,000 | 3=$2,000 | 4-6=$10,000 | 7-11=$50,000 | 12-18=$100,000 | 19+=$200,000
```
Тело findings было верным — ошибка только в summary. Плюс никто не упомянул: **issuer recovery assessment = +$5 за каждый диспут свыше 300**.

**A2. КРИТИЧЕСКОЕ УПУЩЕНИЕ — все 12 исследователей пропустили исключения из VAMP.** Stripe docs дословно: Visa исключает диспут из VAMP count если «The dispute was resolved through pre-dispute products, such as Stripe's dispute prevention» или «The TC40 fraud qualified for Compelling Evidence 3.0». **Это меняет всю антидиспутную стратегию:** RDR/Ethoca-подобная предиспутная отбивка не просто экономит $20 — она физически убирает событие из счётчика VAMP. Единственный инструмент, который реально снижает VAMP ratio. Возврат ПОСЛЕ диспута не снижает ничего.

**A3. EFM: пропущена оговорка по Австралии** — net fraud $15,000 (не $50,000) и fraud rate 0.20% (не 0.50%).

**A4. RevenueCat RLTV — расхождение в чтении таблицы.** Исследователь 2 отнёс $35.89/$6.67 к monthly, а $62.19/$10.69 к yearly. Мой фетч вернул $62.19/$10.69 с меткой monthly. Одно из чтений ошибочно. **Материальность низкая, потому что для планирования брать надо нижнее число в любом случае:** low-priced RLTV = $6.67–10.69.

**A5. Доля IN/SEA — арифметика исследователя 2 верна, моего фетча — нет.** По подтверждённым медианам: monthly 37.5%, annual 45.8%, weekly 65.9%. Диапазон «38-46%» корректен. Пол 0.40 остаётся обоснованным.

### B. ПРЯМОЕ ПРОТИВОРЕЧИЕ МЕЖДУ ИССЛЕДОВАТЕЛЯМИ (решающее для продукта)

**`tweaks_efficacy` против `anticheat_safety` по VBS/HVCI.** Первый ставит «отключение VBS/Memory Integrity» в **TIER_A — «измеримо, продавать»**. Второй говорит **«НИКОГДА не отключать»**, потому что Vanguard при `VAN: RESTRICTION` требует HVCI включённым.

**РЕШЕНИЕ: прав `anticheat_safety`.** `tweaks_efficacy` описывает физику (Microsoft действительно признаёт удар по производительности на CPU без MBEC/GMET), но игнорирует последствие: Valorant — игра №2 в целевом списке. Если поставить это в TIER_A и применять по умолчанию, часть клиентов потеряет доступ к игре. Правило — только ветвление:
```
if (Win11) OR (Win10 AND UEFI AND TPM2.0) -> VBS/HVCI НЕ ТРОГАТЬ
elif (Win10 AND (no UEFI OR no TPM2.0))   -> отключение допустимо (Riot сам предписывает при VAN 9005)
```

**Второе подтверждённое противоречие — между самими вендорами.** BattlEye просит временно отключить Hardware-enforced Stack Protection (Core Isolation), Vanguard требует HVCI. **Единый глобальный «one-click optimize» физически невозможен** — только per-game профили.

### C. ПЛОХИЕ ДАННЫЕ И МИФЫ (все — корректно пойманы исследователями)

- **МИФ ПОДТВЕРЖДЁН ЛОЖНЫМ:** поисковый сниппет «EXM стоит $8.99/мес со скидкой до $4.49/мес». Опровергнуто прямым парсингом: рекуррентных полей в pricingData нет вообще. Урок для скрипта: конкурентные цены читать только из первоисточника.
- **«EV-сертификат сразу снимает SmartScreen»** — в актуальной документации Microsoft (2026) подтверждения нет. Помечено как миф правильно.
- **«Поддерживаем все античиты» (AtlasOS)** — опровергается их же FAQ (FIFA/EAFC требуют Defender, Roblox требует UAC+TPM+Secure Boot).

### D. ВЫДУМАННЫХ ИСТОЧНИКОВ НЕ НАЙДЕНО

Проверил выборочно самые «удобные» цифры — все подтвердились, включая ту, которую я считал наиболее вероятной галлюцинацией (DLSS 5 / NBA 2K27). Исследователи дисциплинированно писали «нет данных» вместо выдумывания.

**Но: `tweaks_efficacy` — самое слабое измерение.** ~8 его находок имеют `source: "нет данных"` и являются inference. Конкретно НЕ подтверждено ничем: ReBAR по играм, проценты XMP/EXPO, стоимость оверлеев в FPS, эффект debloat, эффект плана питания, per-game настройки. **Ни одна цифра оттуда не должна попасть в рекламу без собственного замера.**

---

## 3. ИТОГОВАЯ ПРОДУКТОВАЯ СТРАТЕГИЯ

### 3.1 Что продавать в первую очередь

**Не подписку.** Три независимо подтверждённых факта сходятся:
1. Лидер рынка (EXM) продаёт **lifetime** и на этом построил 171K Discord и ~965K загрузок.
2. Gaming Y1 revenue per payer = **$11.22** — подписка на $5.99 с churn 35% даёт LTV ~$10. То есть подписка не даёт преимущества в LTV, но добавляет диспуты «я забыл отписаться».
3. Твики применяются один раз и продолжают работать после отмены — подписка ценностно не оправдана, и клиент это увидит.

**ПОРЯДОК ЗАПУСКА:**

| Приоритет | Продукт | Цена T1 | Обоснование |
|---|---|---|---|
| **1** | **Lifetime licence, 1 ПК** | **$39.99** | Между Plus ($29.99) и Premium ($49.99) EXM. Касса с холодного клика сразу |
| **2** | **Seat-апселл** 2/3/4 ПК | $69.99 / $94.99 / $119.99 | Шкала EXM (+83%/+150%/+233%) — проверена, стоит 0 в разработке |
| **3** | **Free tier с квотой** | $0 | Механика Hone (10 оптимизаций), не урезание по фичам. Он же материал для коротких видео |
| **4** | **Подписка $4.99/мес** — ТОЛЬКО после ~200 lifetime-продаж | $4.99 | Продавать не твики, а **обновления под патчи**: «профили под новый сезон Fortnite в течение 48ч» |

**НЕ делать в первую очередь:** ручные OC-сессии (EXM берёт €25-120, но это ломает «без ручной работы»), физику (коврики/ноутбуки), игровые аккаунты.

### 3.2 Цены по тирам регионов

```json
{
  "tiers": {"T1": 1.00, "T2": 0.80, "T3": 0.60, "T4": 0.40},
  "classifier": "World Bank NY.GNP.PCAP.PP.CD ratio to USA: >=0.65->T1, 0.45-0.65->T2, 0.25-0.45->T3, <0.25->T4",
  "hard_floor": 0.40,
  "lifetime_1pc": {"T1": 39.99, "T2": 31.99, "T3": 23.99, "T4": 15.99},
  "sub_monthly":  {"T1": 4.99,  "T2": 3.99,  "T3": 2.99,  "T4": 1.99},
  "T1": ["US","CA","GB","AU","NZ","DE","NL","SE","NO","DK","CH","IE","AT","FI","BE","FR","SG","JP","KR","IL","AE","SA","IT","ES"],
  "T2": ["PL","CZ","RO","HU","SK","SI","EE","LV","LT","HR","BG","PT","GR","TR","TW","HK","CL","UY"],
  "T3": ["BR","MX","AR","CO","PE","KZ","MY","TH","RS","GE","AM","UZ"],
  "T4": ["IN","ID","PH","VN","PK","BD","EG","NG","KE","MA","LK","NP","UA","ZA"],
  "geo_detection": "страна платёжного метода/BIN на подтверждении платежа, НЕ только IP",
  "blocked_buyers": ["CF","CU","KP","CD","ER","GW","IR","IQ","LB","LY","ML","RU","SO","SS","SD","SY","YE"]
}
```
Пол 0.40 подтверждён рынком: IN/SEA реально 37.5-45.8% от NA. Определение по BIN обязательно — целевая аудитория сидит в Discord, где обход через VPN разлетается за часы.

### 3.3 Платёжка — решение

```
PADDLE       -> ИСКЛЮЧЁН. AUP дословно запрещает эту категорию. Не строить интеграцию.
STRIPE напрямую -> требует юрлицо вне СНГ. Прецедент: EXM = Slovak s.r.o. Country locked после
                   первого live-платежа — решать ДО запуска.
LEMON SQUEEZY -> РЕКОМЕНДУЕТСЯ КАК СТАРТ, если оператор резидент AM/AZ/KZ/MD/UZ.
                 Выплата на локальный банк, юрлицо не нужно, MoR снимает VAT.
                 Стоимость: 5% + $0.50 +1.5% intl +0.5% sub +1% выплата ≈ 8% + $0.50.
                 Оговорка: пункт "products restricted by our payment processing partners"
                 импортирует ограничения Stripe — маркетинг всё равно должен быть чистым.
GUMROAD      -> только как аварийный резерв (10% + $0.50, нет абонплаты = держать бесплатно).
```

**Если оператор из GE/UA/BY/KG** — пути на банк нет: либо PayPal-выплата у LS, либо UK Ltd/EU-юрлицо. **UK Ltd решает три задачи сразу:** Stripe напрямую, Artifact Signing за $9.99/мес (организациям UK доступно), и позиционирование уже английское.

### 3.4 Авто-выдача (0 ручной работы)

```
webhook (order_created / membership.went_valid)
  -> verify signature
  -> idempotent by order_id
  -> issue licence (HWID activation_limit=2)
  -> email ключ + ссылка на скачивание
  -> Discord OAuth (scope identify+guilds.join) -> PUT roles=[PAID]
  -> запись entitlement

reverse: refund/chargeback/expire -> revoke licence server-side + снять роль
reconcile: hourly cron, диф в обе стороны (плательщик без роли / ушедший с ролью)
self-serve: сброс HWID 1 раз в 90 дней + отмена в один клик — без тикета
```
Ключ дублируется на email и в веб-кабинет. **Discord не должен быть единственным каналом выдачи** — бан сервера не должен ломать доступ платящим.

### 3.5 Честные обещания и дисклеймеры

**РАЗРЕШЕНО (подкреплено измерениями):**
- «1% low +8-48% при открытых Discord/браузере» — замер на i7-13700H/RTX 4060 Laptop, CapFrameX
- «Системная латентность −5…−18 ms, если ты GPU-bound на 60-120 FPS» — LDAT-замеры TFTCentral
- «На слабых картах вроде GTX 1660 Super в 1080p: 56→38 ms» — данные NVIDIA
- «Ниже температуры и меньше троттлинга на ноутбуке» — вместо обещания FPS
- «Подберём пресет апскейлинга — обычно самый большой прирост FPS на слабом GPU»

**ОБЯЗАТЕЛЬНЫЕ ДИСКЛЕЙМЕРЫ (каждый опирается на проверенный источник):**
1. «User-mode only. Мы не ставим kernel-драйверы, не меняем файлы игр, не взаимодействуем с античитом.»
2. «Мы никогда не отключаем Secure Boot, TPM, IOMMU, Core Isolation и Windows Exploit Protection — они требуются Vanguard, EAC, EA Javelin и Call of Duty.»
3. «Результат зависит от железа, игры и настроек. Цифры измерены на указанных системах.»
4. Чекбокс EU/UK: «I request immediate access and acknowledge I lose my 14-day right of withdrawal» — с логом timestamp+IP.
5. «Мы не продаём читы, макросы, HWID-спуферы, разбаны и аккаунты.»

---

## 4. СПИСОК ЗАПРЕТОВ

### 4.1 В ПРОДУКТЕ (hard-блок в коде, без «advanced mode»)

```
НИКОГДА: отключение Secure Boot | отключение/очистка TPM | UEFI->Legacy/CSM
         отключение IOMMU / VT-d / AMD-Vi / DMA Protection
         bcdedit testsigning|nointegritychecks|debug | Driver Verifier
         отключение driver signature enforcement | правки BCD/measured boot
         отключение UAC (EnableLUA=0)  <- ломает Roblox и обновление Vanguard
         отключение Windows Defender  <- ломает FIFA/EAFC
         отключение Exploit Protection (DEP/CFG/ASLR/SEHOP/heap) <- VAN 9002
         повышение PL1/PL2, MCE, множители <- BSOD vgk.sys на Intel 13/14 gen
         ЛЮБОЙ собственный .sys / kernel-драйвер
         зависимость от WinRing0/inpout/ntiolib/winio для чтения температур
```
**Обоснование последних двух — подтверждено дважды:** блок-лист Microsoft включён по умолчанию с Win11 2022 Update, а EA Javelin держит `winring0x64.sys` в публичном denylist.

**НЕ ТРОГАТЬ службы:** `vgc, vgk, EasyAntiCheat, BEService, BEDaisy, EAAntiCheat, WinDefend, SecurityHealthService, tbs`

**НЕ ДЕЛАТЬ (снейк-ойл, режет доверие и попадает в критерии Microsoft):** чистка реестра, RAM-бустеры, дефраг SSD, «сетевые твики для снижения пинга», сканер «найдено 2847 проблем».

**ЗАПРЕЩЁННЫЕ ФИЧИ (иначе продукт = cheat/ban-evasion tool → блокировка платёжки):** HWID-спуфинг, обход банов, разбан-сервисы, макросы/anti-recoil, reWASD-класс ремапперы, SOCD/null-cancel, чтение/запись памяти игры, DLL-инжект.

### 4.2 В РЕКЛАМЕ

```regex
БЛОК: (\+|плюс\s*)\d{2,}\s*(FPS|фпс)   без hardware-контекста
      x2 FPS | double your FPS | удвой FPS
      (lower|reduce|fix)\s+(your\s+)?ping | снизим пинг
      registry clean | чистка реестра | defrag SSD | RAM booster
      zero input lag | 0 ms input lag | нулевой инпут лаг
      undetected | bypass | обход античита | ban-proof | 100% ban safe
      HWID spoof | unban | aimbot | no recoil | aim assist
      guaranteed \+\d+% | works on any PC
      disable Secure Boot|TPM|Defender|Core Isolation
```

**ПОТОЛКИ ЦИФР:** avg FPS ≤ +15% | 1% low ≤ +50% (только с указанием фоновой нагрузки) | латентность ≤ −20 ms / ≤ −35% | **обещания по пингу = 0, запрещены полностью**.

**ВАЛИДАТОР:** любая цифра FPS/ms без всех 6 полей `[cpu, gpu, resolution, game, tool, metric]` блокируется до залива.

**Два анти-паттерна из данных EXM:** продуктовые хуки («You NEED To Get THIS App NOW» = 2.3K против медианы 20K, в ~8 раз хуже) и чит-адъяцентные («This Setting Gives You AIMBOT» = 6.9K + риск страйка). Оба — hard-блок в генераторе.

### 4.3 КАТЕГОРИИ, КОТОРЫЕ РЕЖУТ ПЛАТЁЖКИ

| Категория | Кто режет | Статус |
|---|---|---|
| PC-оптимизаторы / device cleaners | **Paddle (дословно)** | Paddle исключён |
| Игровые аккаунты, in-game currency | Stripe (restricted), PayPal (pre-approval), Epic/Riot/Valve ToS | **Никогда на том же юрлице/аккаунте** |
| «Suspicious remote technical support» | Stripe prohibited | Не продавать удалённые сессии |
| «Outrageous claims / deceptive testimonials / high-pressure upselling» | Stripe prohibited | Лендинг — комплаенс-поверхность |
| IT-услуги лицам в России | Stripe (санкционный пункт) | Гео-блок RU обязателен |
| Продажа читов/хаков | Discord Rule 24 | Бан сервера |

---

## 5. UNIT-ЭКОНОМИКА

**Константы (в конфиг, не хардкод):**
```json
{"geo_blend": 0.79, "fee_rate": 0.08, "fixed_fee_usd": 0.50,
 "refund_rate_lifetime": 0.06, "refund_rate_sub": 0.05,
 "churn_scenarios": [0.25, 0.35, 0.45]}
```

### Lifetime $39.99 (T1)
```
39.99 × 0.79 (гео) = $31.59
− 8% комиссии ($2.53) − $0.50 фикс = $28.56
− 6% возвратов = NET $26.85 за продажу
```

| Цель net/мес | Продаж lifetime/мес |
|---|---|
| $1,000 | **37** |
| $3,000 | **112** |
| $10,000 | **372** |

### Подписка $4.99/мес (T1)
```
4.99 × 0.79 = $3.94  −8% ($0.32) −$0.50 фикс = $3.12  −5% = NET ARPU $2.96
```
**Внимание: фиксированные $0.50 съедают 12.7% гео-скорректированной цены.** На дешёвой подписке фикс — главный убийца маржи, а не процент.

| Цель net/мес | Активных подписок | Новых/мес при churn 25% | 35% | 45% |
|---|---|---|---|---|
| $1,000 | **338** | 85 | 118 | 152 |
| $3,000 | **1,014** | 254 | 355 | 456 |
| $10,000 | **3,378** | 845 | 1,182 | 1,520 |

**LTV подписчика:** churn 25% → $11.84 (4.0 мес) | 35% → $8.46 (2.9 мес) | 45% → $6.58 (2.2 мес)

**КЛЮЧЕВАЯ ПРОВЕРКА СХОДИМОСТИ:** мой расчёт снизу даёт LTV $6.58–11.84. Независимый бенчмарк RevenueCat для Gaming даёт Y1 revenue per payer **$11.22** и low-priced monthly RLTV **$6.67–10.69**. **Три независимых метода сходятся на ~$7-11.** Это самая надёжная цифра во всём отчёте — и она означает: платная закупка трафика при таком LTV не сойдётся почти никогда.

### ГИБРИД (рекомендуется) — 60% выручки lifetime / 40% подписка

| Цель net/мес | Lifetime-продаж/мес | + Активных подписок |
|---|---|---|
| $1,000 | **22** | 135 |
| $3,000 | **67** | 405 |
| $10,000 | **224** | 1,351 |

**Почему гибрид:** к $10k только на подписке нужно 845-1,520 НОВЫХ подписок каждый месяц просто чтобы стоять на месте. Lifetime-путь требует 224 продажи/мес без обязательства их повторять — и уже полученные деньги не отзываются при провале трафика.

### Требование к трафику (грубо, при 1.5% click→paid)
67 lifetime-продаж/мес ≈ 4,470 целевых кликов ≈ **~450K просмотров/мес** ≈ 150-450 постов/мес ≈ **5-15 постов/день по сети из 20 каналов**. Реалистично. Но конверсию 1.5% надо **измерить в первые 2 недели**, не закладывать — публичного бенчмарка join→paid для этой ниши не существует.

---

## 6. ДЕСЯТЬ ГЛАВНЫХ ПРЕДУПРЕЖДЕНИЙ

**1. Paddle исключён дословно — проверьте это ПЕРВЫМ.** AUP запрещает «software marketed to repair, maintain, or improve the performance… of an Electronic Device». Это не серая зона. Интеграцию не строить.

**2. Платёжный рельс решается ДО первой строки кода.** Stripe не работает ни в одной стране СНГ (0 из 10), и страна юрлица блокируется навсегда после первого live-платежа. Если оператор резидент KZ/AM/AZ/MD/UZ — Lemon Squeezy работает сразу. Если GE/UA/BY/KG — нужен PayPal-выплата или UK/EU-юрлицо.

**3. Потолок 4 диспута в месяц жёстче любого маркетингового решения.** VAMP помечает non-compliant при 0.5% ПРИ всего 5 диспутах. При 150-600 транзакциях/мес это ~4 диспута. Аудитория 13-24 платит картами родителей — это худший демографический профиль по friendly fraud. **Но найдено смягчение, которое все пропустили:** диспуты, погашенные предиспутными продуктами, ИСКЛЮЧАЮТСЯ из VAMP count. Предиспутная отбивка — единственный рычаг, который реально снижает счётчик.

**4. Главный риск — не баны, а невозможность запустить игру.** Ни один из 5 античитов не банит за твики. Но отключение Secure Boot/TPM/IOMMU/HVCI/Exploit Protection физически заблокирует Valorant, LoL, Black Ops 7, Battlefield 6, Roblox и турниры Fortnite. Вал возвратов без формального нарушения правил.

**5. Единый «one-click optimize» невозможен — это доказано противоречием вендоров.** BattlEye просит отключить Core Isolation, Vanguard требует его включённым. Только per-game профили с ветвлением по ОС/железу.

**6. Собственный kernel-драйвер = смерть продукта.** Блок-лист Microsoft включён по умолчанию с Win11 2022 Update и принудителен при HVCI (который по умолчанию на большинстве новых Win11). WinRing0 уже в публичном denylist EA. Мониторинг — только user-mode (WMI/PDH/PresentMon).

**7. IObit Advanced SystemCare — прямой аналог вашего продукта — УЖЕ в denylist EA Javelin.** Это не гипотеза о репутационном риске категории, а состоявшийся прецедент. Класс «оптимизатор с драйвером» уже в чёрных списках.

**8. Ваш маркетинг — это критерий классификации Microsoft, а не просто реклама.** «Exaggerated claims about your device's health» + требование оплаты за исправление проблем — дословный критерий unwanted software. Обещание «+50 FPS» в UI приложения буквально увеличивает вероятность детекта. Сканер «найдено N проблем» не ставить никогда.

**9. Не копируйте подписку — лидер её не продаёт.** EXM: `purchase_type` = `lifetime` во всех 11 местах. Gaming Y1 revenue per payer $11.22 означает, что подписка не даёт выигрыша в LTV, зато добавляет диспуты «забыл отписаться». Начинайте с lifetime $39.99, подписку добавляйте вторым слоем за обновления под патчи.

**10. Игровые аккаунты угробят весь бизнес, если оказаться на одном юрлице.** Нарушают ToS Epic/Riot/Valve, требуют pre-approval PayPal, ограничены Stripe, и нарушают Discord Rule 24 (бан сервера = потеря всей базы). Epic в 2025-2026 системно судится. Держать полностью отдельно или не делать.

**Бонус-предупреждение:** `tweaks_efficacy` — самое слабое из 12 измерений. ReBAR, XMP-проценты, эффект debloat, per-game настройки не подтверждены первоисточниками. **Ни одна цифра оттуда не должна попасть в рекламу до собственного замера на 3-4 референсных ПК.** Собственные замеры — это одновременно контент, защита от возвратов и юридически чистые цифры.

---

**Источники верификации:** [exmtweaks.com/pricing](https://exmtweaks.com/en-us/pricing) · [exmtweaks.com/refund-policy](https://exmtweaks.com/en-us/refund-policy) · [velocitytweaks.com/premium](https://velocitytweaks.com/premium) · [paddle.com/support/aup](https://paddle.com/support/aup/) · [stripe.com/global](https://stripe.com/global) · [docs.lemonsqueezy.com supported-countries](https://docs.lemonsqueezy.com/help/getting-started/supported-countries) · [docs.stripe.com/disputes/monitoring-programs](https://docs.stripe.com/disputes/monitoring-programs) · [learn.microsoft.com artifact-signing/quickstart](https://learn.microsoft.com/en-us/azure/artifact-signing/quickstart) · [learn.microsoft.com/defender-xdr/criteria](https://learn.microsoft.com/en-us/defender-xdr/criteria) · [learn.microsoft.com driver-block-rules](https://learn.microsoft.com/en-us/windows/security/application-security/application-control/app-control-for-business/design/microsoft-recommended-driver-block-rules) · [help.ea.com/pc/ea-anticheat](https://help.ea.com/en/help/pc/ea-anticheat/) · [battleye.com/support/faq](https://www.battleye.com/support/faq/) · [docs.discord.com enabling-monetization](https://docs.discord.com/developers/monetization/enabling-monetization) · [revenuecat.com/state-of-subscription-apps-2026](https://www.revenuecat.com/state-of-subscription-apps-2026/) · [xda-developers.com DLSS 5](https://www.xda-developers.com/nvidias-rtx-5090-loses-half-its-power-to-dlss-5-and-their-usual-trick-wont-save-it/)

**Не удалось переверифицировать в этой сессии (403/JS-рендер):** страница Fortnite про Secure Boot+TPM+IOMMU от 19.02.2026 и страница Riot про `VAN: RESTRICTION`. Исследователь 3 цитировал их с конкретными ID статей и датами, и они согласуются с подтверждённым направлением EA/Microsoft — оставляю medium confidence, **перепроверить вручную до запуска**, так как обе задают hard-ограничения продукта.
