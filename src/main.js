import CalHeatmap from 'cal-heatmap';
import 'cal-heatmap/cal-heatmap.css';

function initHeatmap() {
  const data = [
  { date: '2025-01-01', value: 1 },
  { date: '2025-01-02', value: 10 },
  { date: '2025-01-03', value: 25 },
  { date: '2025-01-04', value: 50 },
    ];
    const cal = new CalHeatmap();
    cal.paint({
        itemSelector: '#cal-heatmap',
        data: { source:data, x : 'date', y : 'value' },
        date: { start: new Date(new Date().getFullYear(), 0, 1), highlight: [new Date(), // Highlight today
        ], },
        range: 12,
        domain: { type: 'month', gutter: 10 },
        subDomain: { type: 'day', radius: 2, width: 9, height: 9, gutter: 2 },
        scale: {
        color: {
            type: 'threshold',
            range: ['#040404ff', '#abf9efff', '#4ad5e4ff','#38abcfff', '#218a9dff'],
            domain: [1, 10, 25, 50]
        }
        }
    },
    [
    [
        Tooltip,
        {
        text: function (date, value, dayjsDate) {
            return (value ? value : 'No') + ' cards learnt on ' + dayjsDate.format('LL');
        }
        },
    ],
    ]);
}

// This line exposes the initHeatmap function to the global window object,
// allowing it to be called from outside the module, such as from HTML inline scripts.
window.initHeatmap = initHeatmap;