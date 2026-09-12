# Аудит: механика площадок и единый свод правил

Независимая проверка утверждений исследователей по первоисточникам.

# АУДИТ 12 ИЗМЕРЕНИЙ + ЕДИНЫЙ СВОД ПРАВИЛ

Дата аудита: 2026-09-12. Независимая проверка: 19 прямых обращений к первоисточникам (официальные dev-доки, официальные help-страницы, официальные политики, прайсы вендоров) + 6 поисковых запросов. Все проверки ниже — мои собственные, не пересказ исследователей.

---

## 1. ВЕРИФИКАЦИЯ 19 САМЫХ НАГРУЖЕННЫХ УТВЕРЖДЕНИЙ

| # | Утверждение (чьё) | Вердикт | Факт / исправление | Источник проверки |
|---|---|---|---|---|
| 1 | YouTube Data API: 100 `videos.insert`/сутки на проект + 100 `search.list` + 10 000 юнитов (shorts_mechanics, posting_times, network_architecture) | **ПОДТВЕРЖДЕНО дословно** | «Projects that enable the YouTube Data API have a default quota allocation of 100 search.list calls, 100 videos.insert calls, and 10,000 units per day combined for all other endpoints» | developers.google.com/youtube/v3/getting-started (2026-09-12) |
| 2 | Instagram: 100 API-публикаций / скользящие 24 ч на аккаунт (reels_mechanics, posting_times) | **ПОДТВЕРЖДЕНО дословно** | «Instagram accounts are limited to 100 API-published posts within a 24-hour moving period. Carousels count as a single post.» | developers.facebook.com/docs/instagram-platform/content-publishing |
| 3 | Instagram non-messaging квота = `4800 × impressions_24h` (reels_mechanics) | **ПОДТВЕРЖДЕНО дословно** | «Calls within 24 hours = 4800 * Number of Impressions». Следствие «новорег с 0 показов = 0 квоты» — корректный вывод | developers.facebook.com/docs/graph-api/overview/rate-limiting |
| 4 | Private Replies: 750 вызовов/час на аккаунт (reels_mechanics) | **ПОДТВЕРЖДЕНО дословно** | «750 calls per hour per Instagram professional account for private replies to comments on Instagram posts and reels» | там же |
| 5 | TikTok API: 6 запросов/мин на user access_token (tiktok_mechanics, posting_times) | **ПОДТВЕРЖДЕНО дословно** | «Each user access_token is limited to 6 requests per minute.» | developers.tiktok.com/doc/content-posting-api-reference-direct-post |
| 6 | TikTok: неаудированный клиент публикует ТОЛЬКО приватно (tiktok_mechanics, network_architecture) | **ПОДТВЕРЖДЕНО дословно — это блокер архитектуры** | «All content posted by unaudited clients will be restricted to private viewing mode.» | developers.tiktok.com/doc/content-posting-api-get-started |
| 7 | TikTok: дневной кап постов существует, число не раскрыто (posting_times) | **ПОДТВЕРЖДЕНО** | Коды: `spam_risk_too_many_posts`, `spam_risk_user_banned_from_posting`, `reached_active_user_cap`. Caption ≤2200 UTF-16 runes. Форматы: mp4 / quicktime / webm | там же |
| 8 | YouTube Shorts: view с 31.03.2025 = любой старт/реплей, engaged views отдельно (shorts_mechanics) | **ПОДТВЕРЖДЕНО дословно** | «Views will count the number of times a Short starts to play or replay, with no minimum watch time requirement» | support.google.com/youtube/answer/10059070 |
| 9 | Shorts max = 180 с (shorts_mechanics) | **ПОДТВЕРЖДЕНО** | «up to 3 minutes long» | там же |
| 10 | Страйки YouTube: 7 дн / 14 дн / 3 за 90 дн = удаление, страйк живёт 90 дн (shorts_mechanics) | **ПОДТВЕРЖДЕНО дословно (все 4 числа)** | «1 week» / «2 weeks» / «3 strikes in the same 90-day period may result in your channel being permanently removed» / «will not expire until 90 days» | support.google.com/youtube/answer/2802032 |
| 11 | Хэштеги YouTube: >60 → игнорируются ВСЕ; ≤3 над заголовком (shorts_mechanics) | **ПОДТВЕРЖДЕНО дословно** | «If a video or playlist has more than 60 hashtags, we'll ignore each hashtag on that content»; «up to three hashtags… will appear by your video title» | support.google.com/youtube/answer/6390658 |
| 12 | Авто-дубляж YouTube: «35+ исходных, EN→23» (shorts_mechanics) vs «24 исходных, EN→18» (geo_targeting_truth) vs «EN→20, турецкого нет» (guides_multiling) | **ЧАСТИЧНО ЛОЖНО. Прав guides_multiling** | Официально: **24 исходных языка**; с английского — **ровно 20 целевых**: Arabic, Bengali, Dutch, French\*, German\*, Hebrew, Hindi\*, Indonesian\*, Italian\*, Japanese, Korean, Malayalam, Polish, Portuguese\*, Punjabi, Russian, Spanish\*, Tamil, Telugu, Ukrainian. **Турецкого в списке НЕТ.** Про Shorts в доке — нет данных | support.google.com/youtube/answer/15569972 |
| 13 | Reels API-спеки: 3 с–15 мин, ≤300 MB, ≤1920 px, 23-60 fps, ≤25 Mbps, AAC 48 kHz/128 kbps, moov впереди (reels_mechanics) | **ПОДТВЕРЖДЕНО пункт в пункт (все 9 параметров)** | — | developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/media |
| 14 | Официальные сигналы TikTok + «страна — слабый сигнал», «подписчики не фактор» (tiktok_mechanics, geo_targeting_truth) | **ПОДТВЕРЖДЕНО дословно** | «A strong indicator of interest, such as whether a user finishes watching a longer video from beginning to end, would receive greater weight than a weak indicator, such as whether the video's viewer and creator are both in the same country»; «Neither follower count nor whether the account has had previous high-performing videos are direct factors» | newsroom.tiktok.com/en-us/how-tiktok-recommends-videos-for-you |
| 15 | Socialinsider TikTok: 1-5K = 350 просмотров/пост, ER 4.40%, выборка 2 млн видео / 214 507 профилей (tiktok_mechanics, guides_ru_en) | **ПОДТВЕРЖДЕНО пункт в пункт (все 5 тиров + все ER + выборка + янв 2024–дек 2025)** | Плюс явная оговорка самого источника: «данные 2025 подписаны как 2026» | socialinsider.io/blog/tiktok-benchmarks |
| 16 | Meta Spam policy: высокочастотный постинг/создание аккаунтов, engagement-gating, покупка вовлечённости (reels_mechanics) | **ПОДТВЕРЖДЕНО дословно (все 3 пункта)** | «Posting, sharing, engaging with content or creating accounts… either manually or automatically, at very high frequencies»; «Requiring or claiming that users are required to engage with content… before they are able to view or interact with promised content» | transparency.meta.com/policies/community-standards/spam |
| 17 | TikTok CG: запрет автоматизации и мульти-аккаунтинга (tiktok_mechanics, network_architecture — оба не смогли прочитать) | **ПОДТВЕРЖДЕНО, формулировка получена** | Прямо запрещено: «Using automation to run many accounts or send repetitive content»; «Buying or selling followers or engagement»; «automation tools, scripts, or other tricks designed to bypass their systems». Санкция: ограничение публикаций, выпадение из поиска и FYF | tiktok.com/safety/en/policies-and-engagement/integrity-authenticity |
| 18 | Mosseri: watch time + sends per reach + likes per reach (reels_mechanics) | **ПОДТВЕРЖДЕНО (множественные независимые источники 2026)** | Уточнение: sends весят ~3-5× лайков именно для **unconnected reach**; watch time = суммарные секунды включая реплеи, а не 3-секундные просмотры | Hootsuite / Dataslayer / Blck Alpaca, 2026 |
| 19 | Прайсы инфраструктуры (proxy_infra, network_architecture) | **ПОДТВЕРЖДЕНО пункт в пункт** | IPRoyal: residential $1.75/GB, ISP $1.80/proxy, DC $1.39/proxy, mobile $117/мес. Dolphin Anty: $0/5, $10/60, $89/100, $159/300, $299/unlim. ElevenLabs: Free 10k/2 голоса, Starter $6/30k, Creator $11/121k/3, Pro $99/600k/5, Scale $299/1.8M/15, Business $990/6M/25 | iproyal.com/pricing, dolphin-anty.com/pricing, elevenlabs.io/pricing |

### Найдено НОВОГО, чего нет ни у одного из 12 (критично)

**(A) С 2027-02-01 меняются пороги входа в YPP — ни один исследователь этого не указал.**
Новые заявители: **8 000** квалифицированных публичных watch hours за 365 дней **ИЛИ 20 000 000** квалифицированных Shorts-просмотров за 90 дней. Действующие участники YPP под повышенный порог не подпадают. Отдельно подтверждено: с 2027-02-01 для выплат из Shorts Creator Pool нужно **10 000 000** Shorts-просмотров за скользящие 90 дней; при недоборе пауза только на этот месяц, возобновление автоматическое, long-form платит всё время. Плюс новая опция: при таргете рекламодателя на ≤5 каналов креатор получает прямые 45% с этого размещения.
Источники: blog.youtube «YouTube Partner Program updates 2027», support.google.com/youtube/answer/12843009, Exchange4media 2026-08.

**(B) Политика Inauthentic Content НЕ отменена — она расширена 2026-07-16.**
Три официальных «бакета»: (1) generic / repetitive / template-based контент; (2) off-putting / distressing контент; (3) AI-персоны, обсуждающие sensitive topics (здоровье, финансы). Заголовок vidIQ «Inauthentic Content Has Gone!», на который опирается `guides_ru_en`, — **кликбейт, миф**.
Источники: TechCrunch 2026-07-20, support.google.com/youtube/answer/1311392.

**(C) Январь 2026, крупнейшее применение против массового AI-контента: терминировано 16 каналов, ~4,7 млрд суммарных просмотров, 35 млн подписчиков.** `network_architecture` называет «11 каналов + 6 зачищено» (Kapwing) — цифра занижена/из другого среза.

**(D) Лимит переключателя аккаунтов Instagram = 5 на устройство** (два исследователя написали «нет данных»). Множественные независимые вторичные источники 2026 сходятся на 5; официальную help-страницу подтвердить не удалось (client-rendered). Confidence: medium.

---

## 2. ПРОТИВОРЕЧИЯ МЕЖДУ ИЗМЕРЕНИЯМИ — ВЕРДИКТЫ

| Противоречие | Стороны | ВЕРДИКТ |
|---|---|---|
| **Частота постинга** | Buffer (11 млн постов): 11+/нед = +34% просмотров на пост. SocialPilot (1,5 млн): оптимум 2-3/нед. Socialinsider: фактическая медиана 8-23 поста/**месяц**. «Официальная рекомендация TikTok 1-4/день» (пересказ) | **Ложное противоречие — три разных величины.** Buffer меряет корреляцию (селекция: кто постит больше — тот системнее), SocialPilot — ER, Socialinsider — наблюдаемое поведение, не оптимум. **Причинности не показал никто. Алгоритмического лимита частоты не документировано ни на одной платформе.** → в спеку: конфигурируемо, дефолт 2/сутки/канал, потолок 4. Реальный риск от частоты — антиспам, не охват |
| **Время постинга** | Buffer: 18:00-23:00, выходные лучше. Sprout: 14:00-18:00 вт-чт, выходные избегать. Hootsuite: чт 07:00-09:00, сб день. Later: 05:00, окно 03:00-06:00. Metricool: 20:00, «мёртвая зона» 02:00-05:00 | **Разброс между датасетами больше самого эффекта.** Единственная честная количественная оценка во всей отрасли: **+31%** (персональный лучший час vs средний, Buffer). → вес тайминга в скоринге ≤0.10; единственный межисточниковый консенсус — **20:00 local**; единственное жёсткое правило — blackout. **Прямой конфликт Later (03:00-06:00 = лучшее) vs Metricool/Hootsuite (02:00-05:00 = мёртвая зона)** разрешать так: 02:00-04:00 — запрет, 04:00-06:00 — экспериментальный арм B, не дефолт |
| **Cold start: IG 580 vs TikTok 350 на тире 1-5K** | reels_mechanics: IG выгоднее в 1,66×. tiktok_mechanics/guides_ru_en: опираются только на TT 350 | **TT 350 подтверждён мной напрямую. IG 580 — тот же вендор, та же методология, но выборка — бизнес/бренд-профили, не faceless-страницы.** Вердикт: не отбрасывать Instagram на старте, но обе цифры — directional, не константы. На старте вес каналов ~равный, после ~10K — сдвиг в TikTok |
| **Inauthentic content: жива / отменена** | shorts_mechanics: жива, переименована 15.07.2025. guides_ru_en: vidIQ «Has Gone!» | **shorts_mechanics прав. guides_ru_en распространил миф.** Политика активна и расширена 16.07.2026 |
| **Масштаб зачисток на YouTube** | network_architecture: 11 терминаций на 278 известных AI-каналов ⇒ риск низкий | **Цифра неточна (фактически 16 каналов / 4,7 млрд просмотров в январе 2026), но вывод устоял:** на YouTube главный риск — демонетизация и падение раздачи, а не мгновенное удаление сети |
| **Shorts >60 с с Content ID блокируются глобально** | shorts_mechanics: единственный источник socialrails.com | **НЕ ПОДТВЕРЖДЕНО ничем официальным.** Не кодировать как константу; правило ≤58 с оставить как дешёвую страховку, не как факт |
| **Авто-дубляж: 35+/23 vs 24/18 vs 24/20** | три разные цифры у трёх исследователей | **Разрешено проверкой: 24 исходных, EN→20, турецкого нет** (см. п.12 выше) |
| **«Страна аккаунта — сильнейший гео-фактор» vs «страна — слабый сигнал»** | geo_targeting_truth ставит страну в S-tier; TikTok официально относит country setting к сигналам низкого веса | **Оба верны, но об разном.** Страна регистрации формирует **пул кандидатов и первичную когорту**; в **ранжировании** внутри пула вес низкий и официально уступает досмотру. В спеке формулировать именно так, иначе скрипт будет оптимизировать не то |

---

## 3. ВЫДУМАННЫЕ, НЕПРОВЕРЯЕМЫЕ И ТОКСИЧНЫЕ ИСТОЧНИКИ

**Помечено как НЕ ИСПОЛЬЗОВАТЬ в качестве фактов:**

1. **`f9xr.github.io`** — персональный GitHub Pages, единственный источник ключевого утверждения «с 24.08.2026 YouTube считает view с первого кадра для long-form/live». Утверждение load-bearing (на нём построено поле `metric_regime`), но **подтверждения в официальной документации нет**. → не кодировать как факт.
2. **`+98.31% просмотров от фоновой музыки`** (SocialPilot) — фальшивая точность, методология и выборка не раскрыты. Классический недостоверный статистический артефакт. Аудиотрек добавлять надо (Meta официально понижает muted reels), но **не по этой цифре**.
3. **`Socialic`, `PostEverywhere`, `Voqusa`, `Reply200`, `HowSociable`, `Gyre`, `reap.video`, `Creator Essentials`, `SubSub`, `socialrails.com`, `sendshort.ai`, `reshorts.ai`, `shortimize`** — SEO-контент-фермы и вендорские блоги. Именно из них происходят ВСЕ «пороги»: 70% completion, 200-500 первичных зрителей, qualified view = 5 с, волны раздачи, 40-50% веса watch time, 7-14/14-30/30-90 дней снятия ограничений. **Ни один не подтверждён официально. Ни один не раскрывает методологию.**
4. **`Amra & Delma (2025)` через SocialPilot** — «видео 3-8 мин = 41% времени просмотра в США» — цепочечная цитата третьего порядка, первоисточник не проверяем.
5. **`Adobe Express, n=807`** — «49% американцев используют TikTok как поисковик» — маркетинговый опрос на 807 человек, процитирован через SocialPilot. Порядок величины возможен, цифра — нет.
6. **`arXiv:2604.00994`** (geo_targeting_truth) — ID не подтверждён; в отличие от него `arXiv:2201.12271` (Boeker & Urman) и `arXiv:2501.17831` (TikTok/выборы) — реальные и качественные работы.
7. **`Kapwing: 59% TikTok FYP = AI slop`** — выборка 500 видео на платформу. Directional, не метрика.
8. **Все заявленные доходы faceless-гайдов** ($1 620 985 / 4 канала; $45 186 за 30 дней; $116K за 30 дней) — без скриншотов, без названий каналов, непроверяемо. **В финмодель не вносить ни одну цифру.**
9. **RU-вендоры автозалива (LuxuryTool, NEXO, Paranoya)** — обещание «100-200+ каналов без банов» при 250-771 просмотрах на собственном рекламном ролике. Маркетинг/скам.
10. **Прайсы GeeLark, SOAX, DataImpulse, HeroSMS, закрытие SMS-Activate 29.12.2025** — в этом аудите **не проверялись**, помечены unverified.
11. **«Реки» (rivers) как модель раздачи TikTok** (один RU-источник, 8 698 просмотров) — не подтверждается нигде. Не кодировать.
12. **«Publer: нативный планировщик TikTok ~10 постов/месяц»** — формулировка неоднозначна даже у самого исследователя. Unverified.

**Системное смещение корпуса:** минимум 5 из 12 исследователей сообщили, что бюджет WebSearch был исчерпан, а публичные поисковики отдали CAPTCHA/403. Следствие: корпус **сильно перевешен в сторону (а) официальных dev-доков — они все подтвердились, и (б) SEO-блогов — они не подтверждаются**. Практического ground truth (реальный hit rate сети, burn rate аккаунтов, часы на канал) в корпусе **нет вообще**. Мой аудит это подтверждает: всё, что кодируемо как константа, — из официальных доков; всё «эвристическое» — вендорское.

---

## 4. ЕДИНЫЙ СВОД МАШИННЫХ ПРАВИЛ И КОНСТАНТ

```json
{
  "VERIFIED_HARD_LIMITS": {
    "youtube": {
      "videos_insert_per_project_per_day": 100,
      "search_list_per_project_per_day": 100,
      "other_units_per_day": 10000,
      "quota_reset_tz": "America/Los_Angeles",
      "quota_reset_hour": 0,
      "unit_costs": {"videos.insert": 1600, "videos.update": 50, "thumbnails.set": 50,
                     "playlistItems.insert": 50, "commentThreads.insert": 50,
                     "captions.insert": 400, "videos.list": 1, "channels.list": 1},
      "captions_policy": "BURN_IN_ONLY  // captions.insert = 400 юнитов = 25 вызовов убивают всю суточную квоту",
      "title_max_chars": 100,
      "title_forbidden_chars": ["<", ">"],
      "description_max_BYTES": 5000,
      "tags_total_max_chars": 500,
      "hashtags_hard_limit": 60,
      "hashtags_target": [2, 5],
      "hashtags_shown_above_title": 3,
      "shorts_max_duration_sec": 180,
      "shorts_claim_safe_max_sec": 58,
      "shorts_target_duration_sec": [12, 25],
      "uploads_per_session_ui_max": 15,
      "daily_upload_limit_per_channel": null,
      "daily_upload_limit_handling": "detect 'Upload limit reached' -> cooldown_until = now+24h+jitter, switch channel",
      "strike_1_freeze_days": 7,
      "strike_2_freeze_days": 14,
      "strike_kill_count_per_90d": 3,
      "strike_ttl_days": 90,
      "one_api_project_per_api_client": true,
      "multi_project_quota_scaling": "POLICY_VIOLATION (Dev Policies III.D.1.c)",
      "unique_title_required": "Dev Policies III.C.3 — запрет одинаковых дефолтных заголовков"
    },
    "tiktok": {
      "rate_limit_per_user_token_per_min": 6,
      "script_rate_limit_per_min": 4,
      "unaudited_client_visibility": "SELF_ONLY  // BLOCKER: публичный автозалив через официальный API невозможен без аудита",
      "daily_post_cap": null,
      "error_codes_to_handle": ["spam_risk_too_many_posts", "spam_risk_user_banned_from_posting",
                                "reached_active_user_cap", "unaudited_client_can_only_post_to_private_accounts"],
      "caption_max_utf16_runes": 2200,
      "allowed_mime": ["video/mp4", "video/quicktime", "video/webm"],
      "max_file_bytes": 4294967296,
      "chunk_min_bytes": 5242880,
      "chunk_max_bytes": 67108864,
      "final_chunk_max_bytes": 134217728,
      "max_chunks": 1000,
      "chunk_upload": "STRICTLY_SEQUENTIAL",
      "upload_url_ttl_sec": 3600,
      "fps_range": [23, 60],
      "resolution_px_range": [360, 4096],
      "scheduling_supported": false,
      "pull_from_url_requires_domain_verification": true,
      "PREFLIGHT_MANDATORY": "GET /creator_info/query/ перед КАЖДЫМ постом -> взять privacy_level[] и max_video_post_duration_sec; хардкод = гарантированная ошибка",
      "own_watermark_allowed": false
    },
    "instagram": {
      "api_posts_per_24h_rolling": 100,
      "api_carousel_posts_per_24h": 50,
      "carousel_max_items": 10,
      "quota_formula": "calls_24h = 4800 * impressions_24h",
      "cold_start_deadlock": "impressions_24h == 0 -> API-квота = 0 -> новорег НЕ управляется официальным API",
      "check_endpoint": "GET /content_publishing_limit  // не считать локально",
      "private_replies_per_hour_per_account": 750,
      "private_replies_live_per_sec": 100,
      "send_api_text_per_sec": 100,
      "send_api_media_per_sec": 10,
      "conversations_api_per_sec": 2,
      "script_safe_dm_rate_per_hour": [100, 200],
      "dm_max_BYTES": 1000,
      "dm_reply_window_hours": 24,
      "dm_group_supported": false,
      "reel_duration_sec": [3, 900],
      "reel_cold_reach_max_sec": 90,
      "reel_never_exceed_sec": 180,
      "reel_target_sec": [15, 45],
      "container": ["mp4", "mov"],
      "moov_atom": "FRONT_OF_FILE",
      "edit_lists": false,
      "video_codec": ["h264", "hevc"],
      "gop": "closed", "chroma": "4:2:0", "scan": "progressive",
      "fps_range": [23, 60],
      "max_horizontal_px": 1920,
      "target_resolution": "1080x1920",
      "aspect_range": [0.01, 10.0], "aspect_recommended": "9:16",
      "video_bitrate": "VBR<=25Mbps",
      "max_file_mb": 300,
      "audio": {"codec": "aac", "sample_rate_max_hz": 48000, "channels": [1,2], "bitrate_kbps": 128},
      "licensed_music_via_api": false,
      "audio_source": "EMBEDDED_ORIGINAL_ONLY",
      "required_account_type": ["business", "creator"],
      "account_type_reach_penalty": false,
      "api_flavor": "instagram_api_with_instagram_login",
      "in_app_account_switcher_limit": 5,
      "alt_text_field_available": true
    }
  },

  "POSTS_PER_DAY": {
    "basis": "НЕТ ОФИЦИАЛЬНОГО ЛИМИТА НИ НА ОДНОЙ ПЛАТФОРМЕ. Всё ниже — консервативный дефолт, не алгоритмика.",
    "default_per_channel_per_day": 2,
    "hard_ceiling_per_channel_per_day": 4,
    "ramp_by_account_age_days": {"0-7": 1, "8-30": 2, "31+": 3},
    "min_interval_sec": 10800,
    "min_interval_preferred_sec": 14400,
    "jitter_sec": [-2400, 2400],
    "cron_exact_forbidden": true
  },

  "POSTING_WINDOWS": {
    "timing_weight_in_scoring": {"tiktok": 0.08, "instagram_reels": 0.10, "youtube_shorts": 0.04},
    "max_honest_effect_size": "+31% reach (лучший персональный час vs средний час недели)",
    "storage_rule": "хранить local-time слоты + IANA tz. ХАРДКОД UTC ЗАПРЕЩЁН (DST 2026: EU/UK 2026-10-25, US 2026-11-01)",
    "slots_local": {"S1": "07:30", "S2": "12:30", "S3": "16:00", "S4": "20:00", "S5": "00:00", "S6": "05:00"},
    "arm_A_prime": ["S3", "S4"],
    "arm_B_low_competition": ["S5", "S6"],
    "blackout_local": "02:00-04:59",
    "blackout_note": "Later ставит 03:00-06:00 лучшим окном — прямой конфликт с Metricool/Hootsuite. 04:00-06:00 = только арм B.",
    "utc_matrix": {
      "US_ET_DST_to_2026-11-01": {"S3":"20:00Z","S4":"00:00Z+1","S5":"04:00Z","S6":"09:00Z"},
      "US_ET_STD_from_2026-11-01": {"S3":"21:00Z","S4":"01:00Z+1","S5":"05:00Z","S6":"10:00Z"},
      "US_PT_DST": {"S3":"23:00Z","S4":"03:00Z+1","S5":"07:00Z"},
      "US_blanket_evening": {"summer":"00:00Z-03:00Z","winter":"01:00Z-04:00Z"},
      "UK_BST_to_2026-10-25": {"S1":"06:30Z","S2":"11:30Z","S3":"15:00Z","S4":"19:00Z","S5":"23:00Z","S6":"04:00Z"},
      "UK_GMT_from_2026-10-25": {"S1":"07:30Z","S2":"12:30Z","S3":"16:00Z","S4":"20:00Z","S5":"00:00Z","S6":"05:00Z"},
      "EU_CEST_to_2026-10-25": {"S3":"14:00Z","S4":"18:00Z","S5":"22:00Z"},
      "EU_CET_from_2026-10-25": {"S3":"15:00Z","S4":"19:00Z","S5":"23:00Z"},
      "MENA_Riyadh_UTC+3_noDST": {"S3":"13:00Z","S4":"17:00Z","S5":"21:00Z"},
      "MENA_Dubai_UTC+4": {"S3":"12:00Z","S4":"16:00Z","S5":"20:00Z"},
      "SEA_UTC+8_noDST": {"S3":"08:00Z","S4":"12:00Z","S5":"16:00Z"},
      "SEA_UTC+7": {"S3":"09:00Z","S4":"13:00Z","S5":"17:00Z"},
      "CIS_Moscow_UTC+3_noDST": {"S3":"13:00Z","S4":"17:00Z","S5":"21:00Z"},
      "LATAM_BR_UTC-3_noDST": {"S3":"19:00Z","S4":"23:00Z","S5":"03:00Z+1"},
      "LATAM_MX_UTC-6_noDST": {"S3":"22:00Z","S4":"02:00Z+1","S5":"06:00Z"}
    },
    "collision_hotspots_utc": ["17:00Z (MENA+CIS прайм)", "19:00Z (UK+EU+BR)", "00:00-04:00Z (US+MX+CO)"],
    "collision_rule": "разнести аккаунты внутри окна по секундам + jitter 7-15 мин; одновременный залив = сигнатура сети",
    "MENA_day_weight_override": {"Thu": 1.2}
  },

  "UNIQUENESS_REQUIREMENTS": {
    "rationale_official": [
      "YouTube: 'channels that upload narrative stories with only superficial differences between them' и 'slideshows that all have the same narration' — прямо названы",
      "YouTube Dev Policies III.C.3: запрет одинаковых дефолтных заголовков",
      "Meta: ранжирующий сигнал 'The percentage of identical content between this post and other posts'",
      "Meta (2026-03): Reels оригинален только при 'on-screen presence from a creator presenting something genuinely new'",
      "Instagram официально понижает видимость watermarked reels, reels с борд                    ерами и muted reels"
    ],
    "MANDATORY_UNIQUE_PER_CHANNEL": ["title (100% по всей сети)", "description", "script_text / VO",
                                      "source_footage_set", "thumbnail_template", "hashtag_pool"],
    "DESIRABLE": ["tts_voice_id", "framing / первый кадр"],
    "MANDATORY_FOR_INSTAGRAM": "on_screen_human_presence  // faceless-геймплей структурно не проходит критерий оригинальности Meta",
    "NOT_A_VARIATION_DO_NOT_SPEND_COMPUTE": ["перестановка сцен", "зеркалирование", "смена скорости",
      "re-encode", "смена только музыки", "смена только TTS-голоса при том же тексте"],
    "RENDER_BANS": ["любой watermark (TikTok/IG/YT)", "letterbox/pillarbox/бордеры", "mute/без аудиодорожки",
                    "низкое разрешение", "один mp4 на несколько каналов"],
    "PER_PLATFORM_RENDER": "отдельный мастер из исходников под каждую платформу; НИКОГДА не переливать экспорт TikTok в Reels",
    "DUPLICATE_GUARD": "pHash видео + SimHash скрипта попарно по всей сети; блок публикации при превышении порога"
  },

  "CREATIVE_CONSTANTS": {
    "hook_window_sec": 3,
    "frame_1_content": "числовой результат (FPS до -> после) + игра; без интро, без логотипа",
    "burned_in_captions": "MANDATORY (≈50% видео смотрят без звука; экранный текст индексируется поиском)",
    "safe_area": "не занимать верхние 12% и нижние 20% кадра",
    "audio_required": true,
    "audio_source": "Commercial Music Library / YouTube Audio Library / собственный лицензированный трек",
    "game_music_in_recording": "OFF (отдельный ползунок Music в Fortnite/Valorant/CS2) — только SFX+голос",
    "length_preset_engagement_sec": [15, 30],
    "length_preset_reach_sec": [60, 180],
    "advertiser_safe": "первые 7 секунд и превью — БЕЗ графической игровой жестокости/крови (критично для DBD/Rust/Tarkov); блэклист сильного мата в title и thumbnail",
    "made_for_kids": "selfDeclaredMadeForKids=false; мониторить videos.list на переопределение (риск для Roblox/Minecraft — MFK убивает комментарии и ссылки = убивает воронку)",
    "hashtags": {"youtube": [2,5], "tiktok": [3,5], "instagram": [3,5],
                 "blacklist": ["#fyp","#foryou","#foryoupage","#viral","#parati","#kesfet"]},
    "cta_rule": "CTA на комментарий/шер. CTA 'поставь лайк' = -60% (Metricool). Лайки как KPI не использовать",
    "ig_send_cta_required": true,
    "seo_slots": ["keyword в первых 5 словах caption", "keyword в экранном тексте первого кадра",
                  "keyword в озвучке/TTS (транскрипт индексируется)", "keyword в display name (IG)"]
  },

  "GEO_FIELDS": {
    "granularity": "COUNTRY (ISO-3166-1 alpha-2). Никаких city/DMA/zip в органической части.",
    "account_country_immutable_after_registration": true,
    "ip_policy": "country-consistent резидентский/мобильный IP как ГИГИЕНА (несоответствие SIM/IP/язык/tz = антифрод-риск), НЕ как гео-рычаг",
    "city_targeted_proxy_for_organic": "ЗАПРЕЩЕНО ПОКУПАТЬ — эффекта нет",
    "precise_gps_permission": false,
    "location_tag": "none",
    "youtube": {"defaultLanguage": "en", "defaultAudioLanguage": "en-GB|en-US",
                "localizations": "EMPTY — переводы сами открывают hi/id/pt/ar пулы",
                "auto_dubbing": "OFF", "recordingDetails.location": "DEPRECATED_2017_DO_NOT_USE",
                "regionRestriction.blocked": "NEEDS_TEST — записываемость не подтверждена"},
    "autodub_coverage_from_EN": ["ar","bn","nl","fr","de","he","hi","id","it","ja","ko","ml","pl","pt","pa","ru","es","ta","te","uk"],
    "autodub_NOT_covered": ["tr"],
    "tiktok_india_alert": "if analytics.country=='IN' and share>2% -> flag BOT_TRAFFIC (TikTok забанен в Индии с 2020-06-29, органический IN невозможен)",
    "india_platform_map": {"tiktok": false, "instagram_reels": true, "youtube_shorts": true},
    "telemetry_per_post": ["account_country","upload_ip_country","post_time_utc","post_time_local","slot_code",
                           "creative_lang_variant","audio_lang","top5_viewer_countries+shares","fyp_share"]
  },

  "HEALTH_CHECK_AND_CIRCUIT_BREAKER": {
    "cadence": "1x/24h на аккаунт",
    "checks": ["account status / strikes", "пометка 'not eligible for the For You feed' по каждому видео",
               "traffic source: доля FYP", "engagedViews / publicViews ratio (YT)", "follower vs non-follower reach (IG)"],
    "fyp_share_ok": [0.60, 0.80],
    "fyp_share_alert": 0.10,
    "metrics_first_pull_delay_h": 48,
    "metrics_final_pull_delay_h": 168,
    "compare_only_within_duration_buckets_sec": [[0,20],[21,40],[41,60],[61,180]],
    "state_machine": ["ACTIVE","WARNED","STRIKE1_FREEZE_8D","STRIKE2_FREEZE_15D_OUT_OF_ROTATION_90D",
                      "QUARANTINE_14D","COOLDOWN_24H","RETIRED"],
    "on_yt_strike_1": "freeze 8 дней (официально 7 + запас)",
    "on_yt_strike_2": "freeze 15 дней + вывод из ротации на 90 дней",
    "on_yt_strike_2_active": "QUARANTINE — не заливать вообще, 3-й страйк = потеря канала",
    "on_tiktok_strike": "пауза >=90 дней (TTL страйка)",
    "on_ineligible_flag": "заморозка канала 14 дней (официальных сроков снятия НЕ СУЩЕСТВУЕТ)",
    "on_fyp_share_lt_0.10_twice": "пауза + ручная проверка",
    "on_upload_limit_reached": "cooldown_until = now+24h+jitter, переключить канал",
    "on_ig_quota_zero": "ACCOUNT_STATE_WARMUP — API-планировщик не трогает аккаунт",
    "geo_kill_switch": "if share(target_geo_views) < 0.30 after 10 publications -> RETIRE, создать новый",
    "third_party_shadowban_checkers": "FORBIDDEN — доступа к системам платформ у них нет"
  },

  "HARD_BANS_IN_SCRIPT": [
    "покупка просмотров/лайков/подписчиков/комментариев (прямое нарушение Fake engagement + Meta Spam + TikTok CG)",
    "взаимная подписка между собственными каналами сети (sub4sub)",
    "массовые однотипные комментарии с каналов сети под чужими видео",
    "перекрёстные ссылки/упоминания между каналами сети",
    "несколько каналов в одном Google-аккаунте (YouTube терминирует 'all associated channels')",
    "общие recovery email / платёжные инструменты / device fingerprint между аккаунтами",
    "engagement-gating ('комментируй X чтобы получить ссылку') — прямой пункт Meta Spam policy; ссылка ДОЛЖНА быть доступна и в bio",
    "масштабирование квоты YouTube через N Cloud-проектов на одного API-клиента (Dev Policies III.D.1.c)",
    "сторонние shadowban-чекеры",
    "распространение модифицированных Windows-сборок / кастомных ISO (лицензия MS + риск платёжки)",
    "ссылка на домен с игровыми аккаунтами из bio/описания (YouTube External links policy: 'unauthorized access to paid content (games, music, streaming)')"
  ],

  "FUNNEL": {
    "cta_target": "discord_invite + free_download (паттерн подтверждён у всех 3 прямых конкурентов)",
    "never": "с ролика напрямую на оплату",
    "link_layer": "собственный домен-редиректор, уникальный short-link на КАНАЛ и на РОЛИК; не прямой discord.gg",
    "reason": "атрибуция + смена цели без ручной правки 60 bio + потеря канала не ломает воронку",
    "url_hygiene": "прямой HTTPS, без редирект-цепочек (иначе YouTube удаляет ссылку как непроверяемую)",
    "domain_separation": "домен подписки ОТДЕЛЬНО от любых будущих account-shop доменов",
    "autodelivery": "payment webhook -> Discord role + license key, без ручного шага",
    "ig_dm_funnel": "Private Replies API 750/ч/аккаунт, скрипт держит 100-200/ч",
    "not_a_goal": "YPP / AdSense. Shorts RPM $0.01-0.07. Целевая метрика = CTR в bio -> триал -> оплата"
  },

  "ECONOMY_SEEDS": {
    "views_per_post_by_tier_tiktok": {"1-5K": 350, "5-10K": 945, "10-50K": 3240, "50-100K": 9900, "100K-1M": 34900},
    "views_per_post_by_tier_instagram": {"1-5K": 580, "5-10K": 1000, "10-50K": 2460, "50-100K": 6095, "100K-1M": 16035},
    "er_tiktok_by_tier": {"1-5K": 0.0440, "5-10K": 0.0400, "10-50K": 0.0390, "50-100K": 0.0375, "100K-1M": 0.0395},
    "er_instagram_overall": 0.0048,
    "niche_benchmark_shorts_median": {"exm_tweaks": 20000, "paragon_tweaks": 2600, "xnet_tweaks": 1600},
    "new_channel_target_median": [1500, 3000],
    "organic_decay_multiplier_yoy": [1.30, 1.45],
    "account_growth_rate": "только ~44% аккаунтов <100K растут за год -> закладывать отбраковку >=50% пула как НОРМУ",
    "conversion_view_to_paid": "НЕТ ДАННЫХ ни в одном источнике — обязателен сквозной трекинг с первого дня",
    "budget_reality": "20-30 активных каналов x 1-2 поста/день на self-hosted стеке укладывается в $200/мес. 60 каналов x 3 поста/день — НЕ укладывается (арифметика: прокси $83-142 + SaaS TTS/монтаж $370+)"
  }
}
```

---

## 5. ИТОГОВЫЙ РАНЖИРОВАННЫЙ СПИСОК ФАКТОРОВ, РЕАЛЬНО ВЛИЯЮЩИХ НА ГЕО ВЫДАЧИ

| Ранг | Фактор | Механизм | Доказательство | Confidence |
|---|---|---|---|---|
| **1** | **Поведение первой когорты (досмотр, реплеи, шеры)** | Официально **перебивает** совпадение по стране | TikTok verbatim: досмотр = strong indicator, same-country = weak indicator | **high** |
| **2** | **Язык озвучки + язык экранного текста** | Физически обнуляет watch-through у нецелевой аудитории ⇒ работает через фактор №1, а не как метаданные | Вывод из №1 + официальная индексация транскрипта/экранного текста | **high** |
| **3** | **Страна аккаунта на этапе РЕГИСТРАЦИИ (SIM MCC / IP)** | Формирует **пул кандидатов и первичную аудиторию**, не ранжирование | TikTok Privacy Policy (SIM и/или IP); Boeker & Urman arXiv:2201.12271 «different locations have a strong impact»; «language does not influence the RS as strong as the location» | **high** (для TikTok), medium (IG), **нет данных** (Shorts) |
| **4** | **Граф подписок / кто взаимодействует** | Сильнейший персонализационный фактор в аудите; единственный **долгоиграющий** гео-якорь | arXiv:2201.12271: «the follow-feature influences the RS the strongest»; IG официально: история взаимодействия с автором = сигнал №2 | **medium-high** |
| **5** | **Платный посев с гео-таргетом (TikTok Spark Ads)** | ЕДИНСТВЕННЫЙ инструмент с точным гео-контролем; вовлечённость навсегда приписывается органическому посту | ads.tiktok.com/help/article/spark-ads verbatim | **high** (механизм), **нет данных** (величина эффекта на последующую органику) |
| **6** | **Языковые метаданные + ОТСУТСТВИЕ localizations** | defaultLanguage/defaultAudioLanguage задают языковой пул; переводы метаданных сами открывают чужие пулы | developers.google.com/youtube/v3/docs/videos | **high** |
| **7** | **Авто-дубляж YouTube = OFF** | Включён по умолчанию, автоматически создаёт hi/id/pt/ar дорожки и **де-геолокализует** англоязычный канал | support.google.com/youtube/answer/15569972 (подтверждено: EN→20 языков) | **high** |
| **8** | **Страновая петля обратной связи Reels** | Официальный входной сигнал: «How much time has viewers from **your country** spent on this reel» — случайная первая когорта самозакрепляется | Meta system card «Instagram Reels Chaining» | **high** |
| **9** | Настройки устройства/аккаунта: язык, country setting, тип устройства | Официально названы сигналами **низкого веса** | TikTok Newsroom verbatim: «receive lower weight… relative to other data points» | **high** (что слабые) |
| **10** | US/UK-специфичные референсы (ping в ms, region servers, $-цены, названия турниров) | Через фактор №1 | inference | medium |
| **11** | Время постинга в целевой tz | **Операционно**, не алгоритмически: определяет, кто физически онлайн в первый час | Официальный сигнал = tz **зрителя**, низкий вес. Максимальный измеренный эффект по отрасли: +31% | medium |
| **12** | Локальные/трендовые звуки | Только косвенно через «sounds» в video information | нет прямых гео-данных | low |
| **13** | Коллаборации/дуэты с локальными аккаунтами | Через фактор №4 | inference, прямых замеров нет | low |
| — | **Z-TIER: ГОРОД IP (New York vs Washington)** | **НУЛЕВОЕ подтверждённое влияние на органику** | 6 независимых доказательств: (a) TikTok verbatim «both in the same **country**»; (b) единственный гео-вход в 4 проверенных system cards Meta — «viewers from your **country**», ни одного city/DMA; (c) YouTube Trending — «the same trending videos to all viewers in the same **country**»; (d) Google определяет IP-локацию как «general area… larger than 3 sq km»; (e) **прямой эксперимент** arXiv:2501.17831 — сотни аккаунтов, per-state VPN + GPS-спуфинг в точки Манхэттена / Collin Co TX / Cobb Co GA, эффект идентичен во всех трёх штатах (t=5.82 / 9.21 / 5.83); (f) подстрановая гранулярность есть ТОЛЬКО в платных кабинетах | **high** (что не влияет) |
| — | Z-TIER: IP каждой отдельной ЗАГРУЗКИ (в отличие от IP регистрации) | **НЕТ ДАННЫХ** ни у платформ, ни в академии. Все аудиты меряют сторону ПОТРЕБЛЕНИЯ, не РАСПРЕДЕЛЕНИЯ | — | **нет данных** |
| — | Z-TIER: location-теги / POI, `recordingDetails.location` | Для игрового оффера бесполезны и сужают пул; поле deprecated с 2017 | — | high |

**Практический вывод по деньгам:** не платить за city-level прокси. Платить за чистые **country-correct** мобильные/резидентские IP. City/DMA — только в платном кабинете.

---

## 6. ДЕСЯТЬ ГЛАВНЫХ ПРЕДУПРЕЖДЕНИЙ

1. **Официальный TikTok API не может публиковать публично без аудита клиента.** «All content posted by unaudited clients will be restricted to private viewing mode» — это не ограничение производительности, это **блокер архитектуры**. Аудит предполагает раскрытие интеграции TikTok, а сеть из 20 покупных аккаунтов противоречит пункту ToS «create only one account for strictly personal purposes». Развилка: либо TikTok-ветка не автоматизируется официально, либо она нарушает ToS. Третьего в документации нет.

2. **Instagram: новорег физически не управляется официальным API.** Квота = `4800 × impressions_24h`. Ноль показов = ноль вызовов. Любой план «день первый — полная автоматизация на свежих IG-аккаунтах» провалится на арифметике, а не на банах.

3. **Модель прямо описана в запретах трёх платформ, дословно.** TikTok CG: «Using automation to run many accounts or send repetitive content». Meta Spam: «creating accounts… either manually or automatically, at very high frequencies». Meta Account Integrity: «Close linkage with a network of accounts», «Owned by the same person or entity as an account that has been disabled», «Empty accounts with prolonged dormancy» (= купленные отлежавшиеся новореги попадают в disable-триггер **до первого поста**). Это не серая зона.

4. **Риск коррелированный, не независимый.** Meta сносит кластерами («removes the inauthentic assets involved in these deceptive networks»), YouTube может терминировать «all associated channels». 20 аккаунтов могут умереть одним событием. Требование: ≥1 источник трафика вне Meta в любой момент времени; биллинг и выдача подписки не зависят ни от одного канала.

5. **Дубликаты убивают сеть быстрее и тише, чем баны.** Один рендер на 20 каналов = ровно тот кейс, который YouTube назвал по имени («slideshows that all have the same narration») и который Meta ранжирует напрямую («percentage of identical content between this post and other posts»). Перестановка сцен, зеркалирование, смена скорости и смена TTS-голоса при том же тексте **не считаются вариацией** — это «minimal changes» по формулировке Spam policy.

6. **Instagram Reels без человека в кадре структурно не проходит критерий оригинальности Meta (2026-03).** Faceless-геймплей на IG — не риск, а архитектурная ошибка. Варианты: один реальный оператор-лицо на 2-4 IG-канала, либо отказ от IG-ветки и перераспределение бюджета в Shorts+TikTok.

7. **Рекламного дохода с сети Shorts не будет — и порог входа в YPP растёт.** С 2027-02-01: Shorts Creator Pool требует 10 млн просмотров/90 дней **на канал**; новые заявители — 8 000 watch hours/365 дней **или 20 млн** Shorts-просмотров/90 дней. Если в финмодели есть строка AdSense — обнулить. Каналы = трафик, деньги = подписка.

8. **Бюджет $50-200/мес не покрывает заявленный объём.** Арифметика по проверенным прайсам: 60 аккаунтов прокси = $83-142/мес (IPRoyal); SaaS-монтаж 600 видео/мес ≈ $414 (Submagic); ElevenLabs Scale $299 даёт всего 15 кастомных голосов на 20 каналов. Полный SaaS-стек ≈ $575/мес. **Сходится только конфигурация: 20-30 активных каналов, 1-2 поста/день, self-hosted (Postiz self-host + локальный TTS + ffmpeg + whisper + Dolphin Anty Starter $10).**

9. **Все «пороги», вокруг которых хочется строить пайплайн, — вендорские модели без методологии.** 70% completion, 200-500 первичных зрителей, qualified view = 5 с, «волны раздачи», 40-50% веса watch time, 7-14/14-30/30-90 дней снятия ограничений, «+98.31% от музыки», «Shorts >60 с с Content ID блокируются глобально» — **ноль официальных подтверждений на все вместе**. Кодировать их как константы = ложная уверенность. Только конфигурируемые параметры с логированием.

10. **Публичные счётчики просмотров инфлированы и не годятся как KPI.** Shorts с 31.03.2025 считают любой старт/реплей без минимума времени; решения по публичным просмотрам приведут к масштабированию провальных креативов. Источник истины — engagedViews / averageViewPercentage / stayed-to-watch через Analytics API, sends_per_reach на IG, доля FYP на TikTok. **Отдельно: конверсия «просмотр → Discord → оплата» не оцифрована НИ В ОДНОМ из 12 измерений и ни в одном найденном источнике — сквозной трекинг (уникальный short-link на канал и на ролик) обязателен с первого дня, иначе вся сеть работает вслепую.**

**Бонус-предупреждение (юридическое, вне гео/залива):** продажа игровых аккаунтов нарушает правила Epic/Riot/Valve и политики PayPal/Stripe, а ссылка на такой домен из описания YouTube отдельно нарушает External links policy («unauthorized access to paid content (games, music, streaming services)») — это основание для страйка. Домен подписки держать полностью отдельно от любых будущих account-shop доменов.

---

**Источники верификации:** [YouTube Data API quota](https://developers.google.com/youtube/v3/getting-started) · [IG Content Publishing](https://developers.facebook.com/docs/instagram-platform/content-publishing) · [Meta Graph rate limiting](https://developers.facebook.com/docs/graph-api/overview/rate-limiting) · [TikTok Direct Post API](https://developers.tiktok.com/doc/content-posting-api-reference-direct-post/) · [TikTok API Get Started](https://developers.tiktok.com/doc/content-posting-api-get-started/) · [Shorts views](https://support.google.com/youtube/answer/10059070) · [YouTube strikes](https://support.google.com/youtube/answer/2802032) · [Auto-dubbing languages](https://support.google.com/youtube/answer/15569972) · [YouTube hashtags](https://support.google.com/youtube/answer/6390658) · [IG Reels media specs](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/media) · [TikTok #ForYou ranking](https://newsroom.tiktok.com/en-us/how-tiktok-recommends-videos-for-you) · [TikTok Integrity & Authenticity](https://www.tiktok.com/safety/en/policies-and-engagement/integrity-authenticity) · [Meta Spam policy](https://transparency.meta.com/policies/community-standards/spam/) · [Socialinsider TikTok benchmarks](https://www.socialinsider.io/blog/tiktok-benchmarks/) · [YPP 2027 changes](https://support.google.com/youtube/answer/12843009?hl=en) · [YouTube monetization policies](https://support.google.com/youtube/answer/1311392?hl=en) · [TechCrunch: AI slop policy clarification](https://techcrunch.com/2026/07/20/youtube-clarifies-policies-around-ai-slop-and-upsetting-videos/) · [IPRoyal pricing](https://iproyal.com/pricing/) · [Dolphin Anty pricing](https://dolphin-anty.com/pricing/) · [ElevenLabs pricing](https://elevenlabs.io/pricing) · [Hootsuite IG algorithm](https://blog.hootsuite.com/instagram-algorithm/)
