/** Shown while a route's chunk is fetched.
 *
 *  Every page is code-split, so the first visit to a route costs a network
 *  round trip; afterwards the chunk is in memory and this never renders again.
 *  That asymmetry is why the placeholder must reserve the space the page will
 *  occupy — it first shipped as a short `py-24` box, which collapsed the layout
 *  and then expanded it when the chunk arrived, so every first visit visibly
 *  jumped while repeat visits did not.
 *
 *  min-h-screen matches the shell in Layout, so the content area keeps its
 *  height across the swap and nothing shifts.
 *
 *  Lives in its own module because two boundaries use it: the one inside
 *  Layout, which keeps the sidebar mounted while a page loads, and the outer
 *  one in App for the signed-out routes that render no shell at all.
 */
export const RouteFallback = () => (
  <div className="flex min-h-screen items-center justify-center">
    <div className="h-6 w-6 animate-spin rounded-full border-2 border-muted border-t-primary" />
  </div>
);
