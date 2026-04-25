# Chart Rendering Tests

## 1. Pie chart

```chart
type: pie
title: Browser Market Share
Chrome: 65
Safari: 18
Firefox: 8
Edge: 5
Other: 4
```

## 2. Bar chart

```chart
type: bar
title: Test Scores by Group
labels: Group 1, Group 2, Group 3, Group 4
Math: 85, 78, 92, 70
Physics: 72, 88, 65, 80
Chemistry: 90, 75, 83, 77
```

## 3. Line chart

```chart
type: line
title: Half-Year Metrics
labels: Jan, Feb, Mar, Apr, May, Jun
Series A: 10, 25, 18, 32, 28, 40
Series B: 5, 15, 22, 19, 35, 30
```

## 4. Area chart

```chart
type: area
title: Server Load
labels: Mon, Tue, Wed, Thu, Fri
CPU: 45, 62, 55, 70, 48
RAM: 30, 48, 42, 58, 35
```

## 5. Bar with no legend, custom colors

```chart
type: bar
title: Metrics
labels: A, B, C, D
Values: 40, 65, 30, 85
legend: false
colors: #FF6B6B, #4ECDC4, #45B7D1, #96CEB4
```

## 6. Wide line chart (full year)

```chart
type: line
title: Annual Trend (Wide Layout)
labels: Jan, Feb, Mar, Apr, May, Jun, Jul, Aug, Sep, Oct, Nov, Dec
Sales: 120, 135, 148, 162, 155, 170, 185, 190, 175, 165, 180, 200
Costs: 90, 95, 100, 110, 105, 115, 120, 125, 118, 112, 122, 135
size: wide
```

## 7. Small pie chart

```chart
type: pie
title: Yes / No
Yes: 72
No: 28
size: small
```

Plain text after the charts — verifying that rendering continues correctly afterward.
