<script lang="ts">
    import { Chart, Svg, Axis, Bars, Spline, Area, Pie, Group, Tooltip } from "layerchart";
    import * as ChartUI from "$lib/components/ui/chart/index.js";
    import { Card, CardContent, CardHeader, CardTitle } from "$lib/components/ui/card/index.js";

    let { type, title, data, config } = $props();

    const xAxisKey = $derived(config.xAxisKey);
    const yAxisKeys = $derived(config.yAxisKeys || []);

    // Create a chart config for the UI components
    const chartConfig = $derived(yAxisKeys.reduce((acc: any, key: string, i: number) => {
        acc[key] = {
            label: key.charAt(0).toUpperCase() + key.slice(1),
            color: `hsl(var(--chart-${(i % 5) + 1}))`
        };
        return acc;
    }, {}));
</script>

<Card class="w-full mt-4">
    <CardHeader>
        <CardTitle>{title}</CardTitle>
    </CardHeader>
    <CardContent>
        <ChartUI.ChartContainer config={chartConfig} class="aspect-[16/9] w-full">
            <Chart 
                {data} 
                x={xAxisKey} 
                y={yAxisKeys[0]} 
                padding={{ left: 16, bottom: 24, top: 16, right: 16 }}
            >
                <Svg>
                    <Axis placement="bottom" grid={{ class: "stroke-muted/20" }} />
                    <Axis placement="left" grid={{ class: "stroke-muted/20" }} />
                    
                    {#if type === "bar"}
                        <Bars radius={4} strokeWidth={0} fill="var(--color-primary)" />
                    {:else if type === "line"}
                        <Spline strokeWidth={2} stroke="var(--color-primary)" />
                    {:else if type === "area"}
                        <Area line={{ strokeWidth: 2, stroke: "var(--color-primary)" }} fill="var(--color-primary)" fill-opacity={0.2} />
                    {:else if type === "pie"}
                        <Group center>
                            <Pie />
                        </Group>
                    {/if}
                </Svg>
                <Tooltip.Root>
                    <ChartUI.Tooltip />
                </Tooltip.Root>
            </Chart>
        </ChartUI.ChartContainer>
    </CardContent>
</Card>
