-- Q1: самые просматриваемые задачи за день
SELECT task_id, count() AS views
FROM ugc.events_bench
WHERE event_type = 'task.viewed' AND event_time >= '2026-10-15' AND event_time < '2026-10-16'
GROUP BY task_id ORDER BY views DESC LIMIT 10;

-- Q2: уникальные пользователи по дням за месяц
SELECT toDate(event_time) AS day, uniqExact(user_id) AS users
FROM ugc.events_bench
GROUP BY day ORDER BY day;

-- Q3: средняя оценка задач, у которых не меньше 20 оценок
SELECT task_id, avg(rating) AS avg_rating, count() AS ratings
FROM ugc.events_bench
WHERE event_type = 'task.rated'
GROUP BY task_id HAVING ratings >= 20
ORDER BY avg_rating DESC, ratings DESC LIMIT 10;
