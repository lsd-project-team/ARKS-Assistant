/* 表结构 */
CREATE TABLE IF NOT EXISTS cap
(
date DATE,
time TIME,
count INT NOT NULL DEFAULT 0,
PRIMARY key(date, time)
);

/* 将Capacity表的数据复制到cap表中。*/
INSERT INTO cap(date, time, count) 
SELECT DATE(date), TIME(date), count
FROM Capacity;

/* 3, 4, 5, 6 四天的产量。*/
SELECT d.date, d.count AS dayshift, n.count AS neightshift
FROM 
     (/* 白班的产量。 */
       SELECT date, SUM(count) AS COUNT
       FROM cap
	   WHERE date IN ('2015-11-03', '2015-11-04', '2015-11-05', '2015-11-06') AND time>='08:30:00' and time<'20:30:00'
	   GROUP BY date
     )
		 AS d
     JOIN
     (/* 夜班的产量。 */
       SELECT date, first_segment + second_segment AS count
       FROM 
            (
              SELECT s1.date AS date, s1.count AS first_segment, IFNULL(s2.count, 0) AS second_segment
              FROM 
                   (/* 夜班前半段的产量 */
                     SELECT date, SUM(count) AS count
                     FROM cap
                     WHERE date IN ('2015-11-03', '2015-11-04', '2015-11-05', '2015-11-06') AND time>='20:30:00'
                     GROUP BY date
                   )
                   AS s1
                   LEFT OUTER JOIN
                   (/* 夜班后半段的产量 */
                     SELECT DATE(date, '-1 days') AS date, SUM(count) AS count
                     FROM cap
                     WHERE date IN ('2015-11-04', '2015-11-05', '2015-11-06', '2015-11-07') AND time<'08:30:00'
                     GROUP BY date
                   )
                   AS s2
                   ON s1.date=s2.DATE
             UNION 
              SELECT s2.date AS date, IFNULL(s1.count, 0) AS first_segment, s2.count AS second_segment
              FROM 
                   (/* 夜班后半段的产量 */
                     SELECT DATE(date, '-1 days') AS date, SUM(count) AS count
                     FROM cap
                     WHERE date IN ('2015-11-04', '2015-11-05', '2015-11-06', '2015-11-07') AND time<'08:30:00'
                     GROUP BY date
                   )
                   AS s2
                   LEFT OUTER JOIN
                   (/* 夜班前半段的产量 */
                     SELECT date AS date, SUM(count) AS count
                     FROM cap
                     WHERE date IN ('2015-11-03', '2015-11-04', '2015-11-05', '2015-11-06') AND time>='20:30:00'
                     GROUP BY date
                   )
                   AS s1
                   ON s1.date=s2.date
            )
     )
		 AS n
     ON d.date=n.date
;





/* 3, 4, 5, 6 四天的产量。*/
SELECT d.date, d.count AS dayshift, n.count AS neightshift
FROM (/* 白班的产量。 */
       SELECT date, SUM(count) AS COUNT
       FROM cap
	   WHERE date IN ('2015-11-03', '2015-11-04', '2015-11-05', '2015-11-06') AND time>='08:30:00' and time<'20:30:00'
	   GROUP BY date
     )
	 AS d
     JOIN
     (/* 夜班的产量。 */
		SELECT date, SUM(count) AS count
		FROM (
			  SELECT date, SUM(count) AS count 
		      FROM cap
			  WHERE date IN ('2015-11-03', '2015-11-04', '2015-11-05', '2015-11-06') AND time>='20:30:00'
			  GROUP BY date

			  UNION

			  SELECT DATE(date, '-1 days') AS date, SUM(count) AS count
			  FROM cap
			  WHERE date IN ('2015-11-04', '2015-11-05', '2015-11-06', '2015-11-07') AND time<'08:30:00'
			  GROUP BY date
			 )
		GROUP BY date
     )
	 AS n
     ON d.date=n.date
;



/* N天的产量。*/
SELECT date, SUM(count)
FROM (
		/* 白班的产量。 */
		SELECT date, SUM(count) AS COUNT
		FROM cap
		WHERE date IN ('2015-11-02', '2015-11-03', '2015-11-04')
			  AND time>='08:30:00' and time<'20:30:00'
		GROUP BY date

		UNION

		/* 夜班的产量。 */
		SELECT date, SUM(count) AS count
		FROM (
				SELECT date, SUM(count) AS count 
		        FROM cap
			    WHERE date IN ('2015-11-02', '2015-11-03', '2015-11-04')
					  AND time>='20:30:00'
			    GROUP BY date

				UNION

				SELECT DATE(date, '-1 days') AS date, SUM(count) AS count
				FROM cap
				WHERE date IN ('2015-11-03', '2015-11-04', '2015-11-05')
				      AND
					  time<'08:30:00'
				GROUP BY date
			 )
		GROUP BY date
    )
GROUP BY date
;






            /* N天的产量。*/
            SELECT date, SUM(dayshift_count), SUM(neightshift_count)
            FROM (
                    /* 白班的产量。 */
                    SELECT date, SUM(count) AS dayshift_count, 0 AS neightshift_count
                    FROM cap
                    WHERE date IN ({0})
                          AND
                          time>='08:30:00'
                          AND
                          time<'20:30:00'
                    GROUP BY date

                    UNION

                    /* 夜班的产量。 */
                    SELECT date, 0 AS dayshift_count, SUM(count) AS neightshift_count
                    FROM (
                           /* 夜班前段的产量 */
                           SELECT date, SUM(count) AS count 
                           FROM cap
                           WHERE date IN ('2015-11-02', '2015-11-03', '2015-11-04', '2015-11-05', '2015-11-06')
                                 AND
                                 time>='20:30:00'
                           GROUP BY date

                           UNION

                           SELECT DATE(date, '-1 days') AS date, SUM(count) AS count
                           FROM cap
                           WHERE date IN ('2015-11-03', '2015-11-04', '2015-11-05', '2015-11-06', '2015-11-07')
                                 AND
                                 time<'08:30:00'
                           GROUP BY date
                         )
                     GROUP BY date
                 )
            GROUP BY date