<script lang="ts">
    import { Chart, Svg, Axis, Bars, Spline, Area, Pie, Arc, Group, Tooltip, Points, PieChart } from "layerchart";
    import * as ChartUI from "$lib/components/ui/chart/index.js";
    import { Card, CardContent, CardHeader, CardTitle } from "$lib/components/ui/card/index.js";

    let { type, title, data, labelKey, valueKeys } = $props();

    const parsedData = $derived(
        data.map((item: any) => {
            const newItem = { ...item };
            valueKeys.forEach((key: string) => {
                if (newItem[key] !== undefined) {
                    const parsed = Number(newItem[key]);
                    if (!Number.isNaN(parsed)) {
                        newItem[key] = parsed;
                    }
                }
            });
            return newItem;
        })
    );

    // Create a chart config for the UI components
    const chartConfig = $derived.by(() => {
        if (type === "pie") {
            return parsedData.reduce((acc: any, item: any) => {
                const key = item[labelKey];
                if (!acc[key]) {
                    acc[key] = {
                        label: key,
                        color: `var(--color-chart-${(Object.keys(acc).length % 5) + 1})`
                    };
                }
                return acc;
            }, {});
        }
        return valueKeys.reduce((acc: any, key: string, i: number) => {
            acc[key] = {
                label: key.charAt(0).toUpperCase() + key.slice(1),
                color: "var(--color-primary)"
            };
            return acc;
        }, {});
    });

    // Range of colors for Pie chart using the theme's chart colors
    const pieRange = [
        'var(--color-chart-1)',
        'var(--color-chart-2)',
        'var(--color-chart-3)',
        'var(--color-chart-4)',
        'var(--color-chart-5)'
    ];
</script>

<Card class="w-full">
    <CardHeader>
        <CardTitle>{title}</CardTitle>
    </CardHeader>
    <CardContent>
        {#if type === "pie"}
            <ChartUI.ChartContainer config={chartConfig} class="aspect-video w-full">
                <PieChart 
                    data={parsedData} 
                    key={labelKey}
                    value={valueKeys[0]}
                    c={labelKey}
                    cRange={pieRange}
                />
            </ChartUI.ChartContainer>
        {:else}
            <ChartUI.ChartContainer config={chartConfig} class="aspect-[16/9] w-full">
                <Chart 
                    data={parsedData} 
                    x={labelKey} 
                    y={valueKeys[0]} 
                    padding={{ left: 16, bottom: 48, top: 16, right: 16 }}
                >
                    <Svg>
                        <Axis 
                            placement="bottom" 
                            grid={{ class: "stroke-muted/20" }} 
                            tickLabelProps={{ 
                                rotate: -45, 
                                textAnchor: 'end', 
                                verticalAnchor: 'middle',
                                dx: -4,
                                dy: 4
                            }}
                        />
                        <Axis placement="left" grid={{ class: "stroke-muted/20" }} />
                        
                        {#if type === "bar"}
                            <Bars radius={4} strokeWidth={0} fill="var(--color-primary)" />
                        {:else if type === "line"}
                            <Spline strokeWidth={2} stroke="var(--color-primary)" />
                            <Points r={3} fill="var(--color-primary)" stroke="var(--color-background)" strokeWidth={1} />
                        {:else if type === "area"}
                            <Area line={{ strokeWidth: 2, stroke: "var(--color-primary)" }} fill="var(--color-primary)" fill-opacity={0.2} />
                            <Points r={3} fill="var(--color-primary)" stroke="var(--color-background)" strokeWidth={1} />
                        {/if}
                    </Svg>
                    <Tooltip.Root>
                        <ChartUI.Tooltip />
                    </Tooltip.Root>
                </Chart>
            </ChartUI.ChartContainer>
        {/if}
    </CardContent>
</Card>
