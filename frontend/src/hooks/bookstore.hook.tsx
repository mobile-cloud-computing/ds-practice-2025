import { useEffect, useState } from "react";
import { Book, BookstoreClient, Checkout, CheckoutResponse } from "../Api/bookstoreClient";

export enum AsyncActionType {
    Init = 'INIT',
    Loading = 'LOADING',
    Error = 'ERROR',
    Success = 'SUCCESS',
}

export interface AsyncState<T> {
    state: AsyncActionType;
    payload?: T
    error?: Error | string;
}

const bookstoreClient = new BookstoreClient();

export function useGetBooks() {
    const [state, setState] = useState<AsyncState<Book[]>>({ state: AsyncActionType.Init });
    useEffect(() => {
        fetchBooks();
    }, []);

    async function fetchBooks() {
        setState({ state: AsyncActionType.Loading });
        try {
            const books = await bookstoreClient.getBooks();
            setState({ state: AsyncActionType.Success, payload: books });
        } catch (e) {
            setState({ state: AsyncActionType.Error, error: e as Error });
        }
    }

    return {
        state,
        actions: {
            fetchBooks
        }
    }
}

export function useGetBook() {
    const [state, setState] = useState<AsyncState<Book>>({ state: AsyncActionType.Init });

    async function getBook(id: string) {
        setState({ state: AsyncActionType.Loading });
        try {
            const book = await bookstoreClient.getBook(id);
            setState({ state: AsyncActionType.Success, payload: book });
        } catch (e) {
            setState({ state: AsyncActionType.Error, error: e as Error });
        }
    }

    return {
        state,
        actions: {
            fetchBook: getBook
        }
    }
}

export function useCheckout() {
    const [state, setState] = useState<AsyncState<CheckoutResponse>>({ state: AsyncActionType.Init });

    async function checkout(details: Checkout) {
        setState({ state: AsyncActionType.Loading });
        try {
            const result = await bookstoreClient.checkout(details);
            setState({ state: AsyncActionType.Success, payload: result});
        } catch (e) {
            setState({ state: AsyncActionType.Error, error: e as Error });
        }
    }

    return {
        state,
        actions: {
            checkout
        }
    }
}