<script lang="ts">
	import { Select as SelectPrimitive } from "bits-ui";
	import { cn, type WithoutChild } from "$lib/utils.js";

	let {
		class: className,
		placeholder,
		...restProps
	}: WithoutChild<SelectPrimitive.ValueProps> = $props();
</script>

<SelectPrimitive.Value
	data-slot="select-value"
	class={cn("flex items-center gap-2", className)}
	{placeholder}
	{...restProps}
/>
