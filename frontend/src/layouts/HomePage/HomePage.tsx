import { useEffect } from "react";
import {ExploreTopBooks} from "./components/ExploreTopBooks";
import {Heros} from "./components/Heros";


export const HomePage = () => {
    useEffect(() => {
        console.log('HME mounted');
    }, []);
    return (
        <>
            <ExploreTopBooks/>
            <Heros/>
        </>
    );
}